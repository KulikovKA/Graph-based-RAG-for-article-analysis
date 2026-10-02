"""Диалоги и атомарный приём jobs с owner scope."""

import base64
import hashlib
import json
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.auth import require_owner
from app.api.dependencies import bounded_json, database
from app.api.schemas import AcceptedV1, ConversationInput, ConversationV1, MessageInput, MessageV1
from app.services.auth import Principal
from app.services.conversations import ConversationService
from app.storage.models import AnalysisRun, Conversation, Message, utcnow
from app.storage.repositories import (
    ActiveRunConflict,
    IdempotencyConflict,
    OwnedRepository,
    VersionConflict,
)

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])
DB = Annotated[Session, Depends(database)]
Owner = Annotated[Principal, Depends(require_owner)]
Body = Annotated[dict[str, Any], Depends(bounded_json)]


def decode_cursor(value: str | None) -> tuple[datetime, UUID] | None:
    if value is None:
        return None
    try:
        if len(value) > 256:
            raise ValueError()
        at, identifier = json.loads(base64.urlsafe_b64decode(value))
        return datetime.fromisoformat(at), UUID(identifier)
    except (ValueError, TypeError, UnicodeError):
        raise HTTPException(400, "INVALID_CURSOR") from None


def encode_cursor(at: datetime, identifier: UUID) -> str:
    return base64.urlsafe_b64encode(json.dumps([at.isoformat(), str(identifier)]).encode()).decode()


def conversation_dto(row: Conversation) -> ConversationV1:
    return ConversationV1(
        id=row.id, title=row.title, created_at=row.created_at, updated_at=row.updated_at
    )


@router.get("")
def conversations(
    owner: Owner, db: DB, cursor: str | None = None, limit: int = Query(50, ge=1, le=50)
) -> dict[str, Any]:
    query = select(Conversation).where(Conversation.owner_user_id == owner.user_id)
    after = decode_cursor(cursor)
    if after:
        at, identifier = after
        query = query.where(
            or_(
                Conversation.updated_at < at,
                (Conversation.updated_at == at) & (Conversation.id > identifier),
            )
        )
    rows = list(
        db.scalars(query.order_by(Conversation.updated_at.desc(), Conversation.id).limit(limit + 1))
    )
    return {
        "items": [conversation_dto(row) for row in rows[:limit]],
        "next_cursor": encode_cursor(rows[limit - 1].updated_at, rows[limit - 1].id)
        if len(rows) > limit
        else None,
    }


@router.post(
    "",
    status_code=201,
    response_model=ConversationV1,
    openapi_extra={
        "requestBody": {
            "content": {"application/json": {"schema": ConversationInput.model_json_schema()}}
        }
    },
)
def create_conversation(body: Body, owner: Owner, db: DB) -> ConversationV1:
    try:
        data = ConversationInput.model_validate(body)
    except ValidationError:
        raise HTTPException(422, "INVALID_INPUT") from None
    row = ConversationService(db).create(owner.user_id, title=data.title)
    return conversation_dto(row)


@router.get("/{conversation_id}")
def conversation(conversation_id: UUID, owner: Owner, db: DB) -> dict[str, Any]:
    service = ConversationService(db)
    try:
        row = service.get(owner.user_id, conversation_id)
        idea = service.current_idea(owner.user_id, conversation_id)
    except LookupError:
        raise HTTPException(404, "NOT_FOUND") from None
    runs = list(
        db.scalars(
            select(AnalysisRun.id)
            .where(
                AnalysisRun.conversation_id == conversation_id,
                AnalysisRun.owner_user_id == owner.user_id,
            )
            .order_by(AnalysisRun.created_at.desc(), AnalysisRun.id)
            .limit(20)
        )
    )
    return {
        **conversation_dto(row).model_dump(mode="json"),
        "idea": {
            "id": str(idea.id),
            "version_no": idea.version_no,
            "normalized": idea.normalized_json,
        }
        if idea
        else None,
        "last_runs": [str(identifier) for identifier in runs],
    }


@router.get("/{conversation_id}/messages")
def messages(
    conversation_id: UUID,
    owner: Owner,
    db: DB,
    cursor: str | None = None,
    limit: int = Query(100, ge=1, le=100),
) -> dict[str, Any]:
    if OwnedRepository(db).conversation(owner.user_id, conversation_id) is None:
        raise HTTPException(404, "NOT_FOUND")
    query = select(Message).where(Message.conversation_id == conversation_id)
    after = decode_cursor(cursor)
    if after:
        at, identifier = after
        query = query.where(
            or_(Message.created_at > at, (Message.created_at == at) & (Message.id > identifier))
        )
    rows = list(db.scalars(query.order_by(Message.created_at, Message.id).limit(limit + 1)))
    return {
        "items": [
            MessageV1(
                id=row.id,
                role=row.role,
                content=row.content,
                run_id=row.run_id,
                created_at=row.created_at,
            )
            for row in rows[:limit]
        ],
        "next_cursor": encode_cursor(rows[limit - 1].created_at, rows[limit - 1].id)
        if len(rows) > limit
        else None,
    }


@router.post(
    "/{conversation_id}/messages",
    status_code=202,
    response_model=AcceptedV1,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": MessageInput.model_json_schema()}},
        }
    },
)
def accept_message(
    conversation_id: UUID,
    body: Body,
    owner: Owner,
    db: DB,
    idempotency_key: Annotated[str, Header(min_length=1, max_length=128)],
) -> AcceptedV1:
    content = body.get("content")
    if isinstance(content, str) and len(content.encode("utf-8")) > 8192:
        raise HTTPException(413, "CONTENT_TOO_LARGE")
    try:
        data = MessageInput.model_validate(body)
    except ValidationError:
        raise HTTPException(422, "INVALID_INPUT") from None
    repo = OwnedRepository(db)
    if repo.conversation(owner.user_id, conversation_id) is None:
        raise HTTPException(404, "NOT_FOUND")
    # Повтор ключа проверяется репозиторием раньше version/source-state, сохраняя идемпотентность.
    existing = db.scalar(
        select(AnalysisRun.id).where(
            AnalysisRun.conversation_id == conversation_id,
            AnalysisRun.owner_user_id == owner.user_id,
            AnalysisRun.idempotency_key == idempotency_key,
        )
    )
    if data.source_run_id and existing is None:
        source = repo.get_run(data.source_run_id, owner_id=owner.user_id)
        if source is None or source.conversation_id != conversation_id:
            raise HTTPException(404, "NOT_FOUND")
        if source.status != "completed":
            raise HTTPException(409, "SOURCE_RUN_NOT_COMPLETED")
    request_hash = hashlib.sha256(
        json.dumps(
            data.model_dump(mode="json"), sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode()
    ).hexdigest()
    try:
        run, _ = repo.accept_run(
            owner_id=owner.user_id,
            conversation_id=conversation_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            expected_idea_version=data.expected_idea_version,
            content=data.content,
            query=data.content,
            source_run_id=data.source_run_id,
        )
    except IdempotencyConflict:
        raise HTTPException(409, "IDEMPOTENCY_CONFLICT") from None
    except VersionConflict:
        raise HTTPException(409, "VERSION_CONFLICT") from None
    except ActiveRunConflict:
        raise HTTPException(409, "RUN_IN_PROGRESS") from None
    except LookupError:
        raise HTTPException(404, "NOT_FOUND") from None
    row = repo.conversation(owner.user_id, conversation_id)
    assert row is not None
    row.updated_at = utcnow()
    return AcceptedV1(
        message_id=run.message_id,
        run_id=run.id,
        status_url=f"/api/v1/runs/{run.id}",
        events_url=f"/api/v1/runs/{run.id}/events",
    )
