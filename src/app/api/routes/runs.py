"""GET/cancel/evidence и owner-scoped durable SSE."""

import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool
from starlette.responses import StreamingResponse
from starlette.types import Send

from app.api.auth import COOKIE_NAME, auth_service, require_owner
from app.api.projections import public_run, public_snapshot, source_url
from app.api.routes.conversations import DB, Owner
from app.api.schemas import EVENT_SCHEMAS
from app.domain.contracts import EvidenceV1, RunV1
from app.services.auth import AuthService, Principal
from app.services.export_report import render_export, render_export_pdf
from app.services.run_events import RunEventError, RunEventsService, StoredEvent
from app.storage.jobs import JobRepository
from app.storage.models import AnalysisRun, EvidenceChunk, RunEvidence
from app.storage.repositories import OwnedRepository

router = APIRouter(prefix="/api/v1/runs", tags=["runs"])
TERMINAL = {"completed", "failed", "cancelled"}


@router.get("/{run_id}", response_model=RunV1)
def get_run(run_id: UUID, owner: Owner, db: DB) -> RunV1:
    run = OwnedRepository(db).get_run(run_id, owner_id=owner.user_id)
    if run is None:
        raise HTTPException(404, "NOT_FOUND")
    return public_run(run)


@router.get(
    "/{run_id}/export",
    response_class=Response,
    responses={200: {"content": {
        "text/html": {"schema": {"type": "string"}},
        "application/pdf": {"schema": {"type": "string", "format": "binary"}},
    }}},
)
def export_run(
    run_id: UUID, owner: Owner, db: DB, format: Literal["html", "pdf"] = "html"
) -> Response:
    try:
        run = OwnedRepository(db).get_run(run_id, owner_id=owner.user_id)
        if run is None:
            raise HTTPException(404, "NOT_FOUND")
        if run.status != "completed":
            raise HTTPException(409, "RUN_NOT_COMPLETED", headers={"Cache-Control": "no-store"})
        content = render_export(db, run) if format == "html" else render_export_pdf(db, run)
    except HTTPException as exc:
        if exc.status_code == 503:
            raise HTTPException(
                503, "INVALID_STORED_RESULT", headers={"Cache-Control": "no-store"}
            ) from None
        raise
    except (SQLAlchemyError, ValidationError, ValueError, TypeError, KeyError, AttributeError):
        raise HTTPException(
            503, "INVALID_STORED_RESULT", headers={"Cache-Control": "no-store"}
        ) from None
    return Response(
        content,
        media_type="text/html; charset=utf-8" if format == "html" else "application/pdf",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="run-{run_id}.{format}"',
            "Content-Security-Policy": "default-src 'none'; base-uri 'none'; form-action 'none'",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/{run_id}/cancel")
def cancel(run_id: UUID, owner: Owner, db: DB, response: Response) -> dict[str, Any]:
    if OwnedRepository(db).get_run(run_id, owner_id=owner.user_id) is None:
        raise HTTPException(404, "NOT_FOUND")
    requested = JobRepository(db).request_cancel(run_id, owner_id=owner.user_id)
    run = OwnedRepository(db).get_run(run_id, owner_id=owner.user_id)
    assert run is not None
    db.refresh(run)
    response.status_code = 202 if requested else 200
    return {"status": run.status, "cancel_requested": requested}


@router.get("/{run_id}/evidence/{evidence_id}", response_model=EvidenceV1)
def evidence(run_id: UUID, evidence_id: UUID, owner: Owner, db: DB) -> EvidenceV1:
    if OwnedRepository(db).get_run(run_id, owner_id=owner.user_id) is None:
        raise HTTPException(404, "NOT_FOUND")
    row = db.execute(
        select(RunEvidence, EvidenceChunk.section)
        .join(EvidenceChunk, EvidenceChunk.id == RunEvidence.chunk_id)
        .where(RunEvidence.run_id == run_id, RunEvidence.evidence_id == evidence_id)
    ).first()
    if row is None:
        raise HTTPException(404, "NOT_FOUND")
    item, section = row
    return EvidenceV1(
        evidence_id=item.evidence_id,
        document_id=item.document_id,
        revision_id=item.revision_id,
        chunk_id=item.chunk_id,
        section=section,
        span_start=item.span_start,
        span_end=item.span_end,
        quoted_span=item.quoted_span,
        source_url=source_url(item.source_url),
    )


def replay_batch(
    service: AuthService, principal: Principal, token: str | None, run_id: UUID, cursor: int | None
) -> tuple[list[StoredEvent], bool]:
    current = service.authenticate(token)
    if current is None or current.session_id != principal.session_id:
        raise HTTPException(401, "UNAUTHENTICATED")
    with service.sessions.begin() as db:
        # Shared lock обеспечивает согласованность ownership/snapshot/high-water с compaction.
        run = db.scalar(
            select(AnalysisRun)
            .where(AnalysisRun.id == run_id, AnalysisRun.owner_user_id == principal.user_id)
            .with_for_update(read=True)
        )
        if run is None:
            raise HTTPException(404, "NOT_FOUND")
        try:
            events = RunEventsService(db).replay(run_id, cursor=cursor, limit=16)
        except RunEventError:
            raise HTTPException(400, "INVALID_CURSOR") from None
        return events, run.status in TERMINAL and (cursor or 0) >= run.event_seq_high_water


def event_frame(event: StoredEvent) -> bytes:
    payload = dict(event.payload)
    if event.event_type in TERMINAL or event.event_type == "run_snapshot":
        payload["run"] = public_snapshot(payload["run"]).model_dump(mode="json")
    if event.event_type == "sources_ready":
        for source in payload["sources"]:
            source_url(source["url"])
    schema = EVENT_SCHEMAS.get(event.event_type)
    if schema is None:
        raise ValueError("UNSUPPORTED_EVENT")
    validated = schema.model_validate(payload).model_dump(mode="json", exclude_unset=True)
    envelope = {
        "run_id": str(event.run_id),
        "seq": event.sequence_no,
        "at": event.created_at.isoformat(),
        "payload": validated,
    }
    encoded = json.dumps(envelope, ensure_ascii=False, separators=(",", ":"))
    return f"id: {event.sequence_no}\nevent: {event.event_type}\ndata: {encoded}\n\n".encode()


class BoundedStreamingResponse(StreamingResponse):
    """Без очереди клиента; медленный send закрывает поток, не задерживая worker."""

    send_timeout = 10.0

    async def stream_response(self, send: Send) -> None:
        async def bounded_send(message: Any) -> None:
            await asyncio.wait_for(send(message), timeout=self.send_timeout)

        try:
            await super().stream_response(bounded_send)
        except TimeoutError:
            return
        finally:
            close = getattr(self.body_iterator, "aclose", None)
            if close is not None:
                await close()


async def stream(
    service: AuthService,
    owner: Principal,
    token: str | None,
    run_id: UUID,
    cursor: int | None,
    initial: tuple[list[StoredEvent], bool],
) -> AsyncIterator[bytes]:
    batch, finished = initial
    heartbeat = time.monotonic()
    try:
        while True:
            for event in batch:
                if await run_in_threadpool(service.authenticate, token) is None:
                    return
                yield event_frame(event)
                cursor = event.sequence_no
                if event.event_type in TERMINAL:
                    return
                if (
                    event.event_type == "run_snapshot"
                    and event.payload["run"]["status"] in TERMINAL
                ):
                    return
            if finished:
                return
            if time.monotonic() - heartbeat >= 15:
                yield b": heartbeat\n\n"
                heartbeat = time.monotonic()
            if not batch:
                await asyncio.sleep(0.25)
            batch, finished = await run_in_threadpool(
                replay_batch, service, owner, token, run_id, cursor
            )
    except (HTTPException, SQLAlchemyError, ValidationError, ValueError):
        # После HTTP headers безопаснее закрыть поток; клиент восстановит snapshot через GET.
        return


@router.get(
    "/{run_id}/events",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {"schema": {"type": "string"}}}}},
)
async def events(
    request: Request,
    run_id: UUID,
    owner: Annotated[Principal, Depends(require_owner)],
    service: Annotated[AuthService, Depends(auth_service)],
    last_event_id: Annotated[str | None, Header()] = None,
) -> StreamingResponse:
    cursor = None
    if last_event_id is not None:
        if not last_event_id.isascii() or not last_event_id.isdecimal() or len(last_event_id) > 18:
            raise HTTPException(400, "INVALID_CURSOR")
        cursor = int(last_event_id)
    token = request.cookies.get(COOKIE_NAME)
    try:
        initial = await run_in_threadpool(replay_batch, service, owner, token, run_id, cursor)
    except SQLAlchemyError:
        raise HTTPException(503, "QUEUE_UNAVAILABLE") from None
    return BoundedStreamingResponse(
        stream(service, owner, token, run_id, cursor, initial),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-store",
            "X-Accel-Buffering": "no",
            "Content-Encoding": "identity",
        },
    )
