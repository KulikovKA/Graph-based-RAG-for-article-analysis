"""Согласие на отправку выбранного контекста внешнему провайдеру."""

import asyncio
import time
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session, sessionmaker
from starlette.concurrency import run_in_threadpool

from app.api.routes.conversations import DB, Owner
from app.domain.planner import IdeaV1
from app.domain.synthetic_guard import SYNTHETIC_EXCERPTS, SYNTHETIC_IDEA
from app.services.evidence_pack import EvidencePack
from app.services.guard import Context, Guard, GuardBudget, GuardDenied, References, Scope
from app.services.guard_consent import (
    NOTICE_VERSION,
    ConsentAuthority,
    grant,
    granted,
    owned_run,
    revoke,
)

router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


class ConsentInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    notice_version: Literal["groq_context_v1"]


class ConsentOutput(BaseModel):
    notice_version: Literal["groq_context_v1"] = "groq_context_v1"
    granted: bool


def check_run(db: DB, owner: Owner, run_id: UUID, *, lock: bool = False) -> None:
    if owned_run(db, owner.user_id, run_id, lock=lock) is None:
        raise HTTPException(404, "NOT_FOUND")


@router.get("/{run_id}/external-consent", response_model=ConsentOutput)
def get_consent(run_id: UUID, owner: Owner, db: DB, response: Response) -> ConsentOutput:
    check_run(db, owner, run_id)
    response.headers["Cache-Control"] = "no-store"
    return ConsentOutput(granted=granted(db, run_id) is not None)


@router.post("/{run_id}/external-consent", response_model=ConsentOutput)
def post_consent(
    run_id: UUID, body: ConsentInput, owner: Owner, db: DB, response: Response
) -> ConsentOutput:
    check_run(db, owner, run_id, lock=True)
    grant(db, run_id)
    response.headers["Cache-Control"] = "no-store"
    return ConsentOutput(granted=True)


@router.delete("/{run_id}/external-consent", status_code=204)
def delete_consent(run_id: UUID, owner: Owner, db: DB) -> Response:
    check_run(db, owner, run_id, lock=True)
    revoke(db, run_id)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


class SyntheticAuthority(ConsentAuthority):
    async def context(self, selected: Scope) -> Context:
        return Context(idea=SYNTHETIC_IDEA, excerpts=SYNTHETIC_EXCERPTS)

    async def references(self, selected: Scope) -> References:
        return References(nodes=frozenset(), evidence=frozenset())

    async def evidence(self, selected: Scope) -> tuple[IdeaV1, EvidencePack]:
        raise GuardDenied("GUARD_PORT_MISSING")


def run_is_cancelled(sessions: sessionmaker[Session], scope: Scope) -> bool:
    with sessions() as db:
        run = owned_run(db, scope.owner_id, scope.run_id)
        return (
            run is None
            or run.conversation_id != scope.conversation_id
            or run.status == "cancelled"
            or run.cancel_requested_at is not None
        )


async def cancellation_watch(
    request: Request, sessions: sessionmaker[Session], scope: Scope, cancel: asyncio.Event
) -> None:
    try:
        while not cancel.is_set():
            if await request.is_disconnected() or await run_in_threadpool(
                run_is_cancelled, sessions, scope
            ):
                cancel.set()
                return
            await asyncio.sleep(0.05)
    except Exception:
        cancel.set()


@router.post("/{run_id}/external-consent/synthetic-check")
async def synthetic_check(run_id: UUID, request: Request, owner: Owner, db: DB) -> dict[str, bool]:
    run = owned_run(db, owner.user_id, run_id)
    if run is None:
        raise HTTPException(404, "NOT_FOUND")
    factory = request.app.state.synthetic_guard_port
    if factory is None:
        raise HTTPException(503, "GUARD_PORT_MISSING")
    deadline = time.monotonic() + 15
    cancel = asyncio.Event()
    scope = Scope(owner.user_id, run.conversation_id, run.id, run.index_generation_id or run.id)
    sessions = request.app.state.auth_service.sessions
    authority = SyntheticAuthority(sessions)
    watcher = None
    try:
        consent = await authority.check(owner.user_id, scope)
        if consent is None or not consent.granted or consent.notice_version != NOTICE_VERSION:
            raise GuardDenied("GUARD_SCOPE_OR_CONSENT")
        if await request.is_disconnected() or await run_in_threadpool(
            run_is_cancelled, sessions, scope
        ):
            raise HTTPException(409, "RUN_CANCELLED")
        watcher = asyncio.create_task(cancellation_watch(request, sessions, scope, cancel))
        guard = Guard(
            authority=authority,
            provider=factory(deadline, cancel),
            tools=None,
            notice_version=NOTICE_VERSION,
        )
        await guard.generate(
            principal=owner.user_id,
            scope=scope,
            budget=GuardBudget(max_calls=1, deadline=deadline, cancel=cancel),
        )
        if (
            cancel.is_set()
            or await request.is_disconnected()
            or await run_in_threadpool(run_is_cancelled, sessions, scope)
        ):
            raise HTTPException(409, "RUN_CANCELLED")
    except asyncio.CancelledError:
        cancel.set()
        raise
    except HTTPException:
        raise
    except Exception:
        if cancel.is_set():
            raise HTTPException(409, "RUN_CANCELLED") from None
        raise HTTPException(503, "GUARD_DENIED") from None
    finally:
        if watcher is not None:
            watcher.cancel()
            await asyncio.gather(watcher, return_exceptions=True)
    return {"ok": True}
