"""Диалоги и атомарный приём jobs с owner scope."""

import base64
import hashlib
import json
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from pydantic import Field, ValidationError, field_validator
from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.auth import auth_service, require_owner
from app.api.dependencies import bounded_json, database
from app.api.schemas import AcceptedV1, ConversationInput, ConversationV1, MessageInput, MessageV1
from app.domain.contracts import StrictModel
from app.services.auth import AuthService, Principal
from app.services.chat_lifecycle import ChatBusy, delete_conversation
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
Auth = Annotated[AuthService, Depends(auth_service)]


class RenameInput(StrictModel):
    title: str | None = Field(max_length=160)

    @field_validator("title")
    @classmethod
    def nonblank_title(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("EMPTY_TITLE")
        return value


class RunHistoryItem(StrictModel):
    id: UUID
    status: str
    outcome: str | None
    created_at: datetime
    completed_at: datetime | None
    idea_version_id: UUID | None
    index_generation_id: UUID | None


class RunHistoryPage(StrictModel):
    items: list[RunHistoryItem]
    next_cursor: str | None


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


@router.patch(
    "/{conversation_id}",
    response_model=ConversationV1,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": RenameInput.model_json_schema()}},
        }
    },
)
def rename_conversation(conversation_id: UUID, body: Body, owner: Owner, db: DB) -> ConversationV1:
    try:
        data = RenameInput.model_validate(body)
    except ValidationError:
        raise HTTPException(422, "INVALID_INPUT") from None
    row = db.scalar(
        select(Conversation)
        .where(Conversation.id == conversation_id, Conversation.owner_user_id == owner.user_id)
        .with_for_update()
    )
    if row is None:
        raise HTTPException(404, "NOT_FOUND")
    row.title = data.title
    row.updated_at = utcnow()
    db.flush()
    return conversation_dto(row)


@router.delete("/{conversation_id}", status_code=204)
def remove_conversation(
    conversation_id: UUID, request: Request, owner: Owner, service: Auth
) -> Response:
    try:
        delete_conversation(service.sessions, owner.user_id, conversation_id)
    except LookupError:
        raise HTTPException(404, "NOT_FOUND") from None
    except ChatBusy:
        raise HTTPException(503, "CHAT_BUSY") from None
    except SQLAlchemyError:
        raise HTTPException(503, "QUEUE_UNAVAILABLE") from None
    cache = getattr(request.app.state, "stage_cache", None)
    if cache is not None:
        try:
            cache.invalidate_conversation(owner.user_id, conversation_id)
        except Exception:
            pass
    return Response(status_code=204)


@router.get("/{conversation_id}/runs", response_model=RunHistoryPage)
def conversation_runs(
    conversation_id: UUID,
    owner: Owner,
    db: DB,
    cursor: str | None = None,
    limit: int = Query(50, ge=1, le=50),
) -> RunHistoryPage:
    if OwnedRepository(db).conversation(owner.user_id, conversation_id) is None:
        raise HTTPException(404, "NOT_FOUND")
    query = select(AnalysisRun).where(
        AnalysisRun.conversation_id == conversation_id, AnalysisRun.owner_user_id == owner.user_id
    )
    after = decode_cursor(cursor)
    if after:
        at, identifier = after
        # Курсор может указывать только на существующий run выбранного чата.
        anchor = db.scalar(query.where(AnalysisRun.id == identifier))
        if anchor is None or anchor.created_at != at:
            raise HTTPException(400, "INVALID_CURSOR")
        query = query.where(
            or_(
                AnalysisRun.created_at < at,
                (AnalysisRun.created_at == at) & (AnalysisRun.id < identifier),
            )
        )
    rows = list(
        db.scalars(
            query.order_by(AnalysisRun.created_at.desc(), AnalysisRun.id.desc()).limit(limit + 1)
        )
    )
    return RunHistoryPage(
        items=[
            RunHistoryItem(
                id=row.id,
                status=row.status,
                outcome=row.outcome,
                created_at=row.created_at,
                completed_at=row.completed_at,
                idea_version_id=row.idea_version_id,
                index_generation_id=row.index_generation_id,
            )
            for row in rows[:limit]
        ],
        next_cursor=(
            encode_cursor(rows[limit - 1].created_at, rows[limit - 1].id)
            if len(rows) > limit
            else None
        ),
    )


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
