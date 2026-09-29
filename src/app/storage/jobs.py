"""Постоянные аренды заданий, защита записей и подтверждения outbox по потребителям.

Методы работают в транзакции вызывающего кода; её фиксируют после записи всех
связанных строк. Токен аренды действует только до истечения её срока.
"""

from datetime import timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.storage.models import AnalysisJob, AnalysisRun, OutboxAck, OutboxEvent, utcnow


class JobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def claim(self, run_id: UUID, *, worker: str, duration: timedelta) -> int | None:
        if duration <= timedelta(0):
            raise ValueError("lease duration must be positive")
        job = self.session.scalar(
            select(AnalysisJob).where(AnalysisJob.run_id == run_id).with_for_update()
        )
        if job is None:
            return None
        run = self.session.scalar(
            select(AnalysisRun).where(AnalysisRun.id == run_id).with_for_update()
        )
        assert run is not None
        now = utcnow()
        if run.status not in ("pending", "running") or run.cancel_requested_at is not None:
            return None
        if job.next_attempt_at > now or (job.lease_until is not None and job.lease_until > now):
            return None
        job.lease_token += 1
        job.attempts += 1
        job.lease_owner = worker
        job.lease_until = now + duration
        job.heartbeat_at = now
        run.status = "running"
        self.session.flush()
        return job.lease_token

    def _fenced(
        self, run_id: UUID, *, worker: str, token: int
    ) -> tuple[AnalysisJob, AnalysisRun] | None:
        job = self.session.scalar(
            select(AnalysisJob).where(AnalysisJob.run_id == run_id).with_for_update()
        )
        if job is None:
            return None
        run = self.session.scalar(
            select(AnalysisRun).where(AnalysisRun.id == run_id).with_for_update()
        )
        assert run is not None
        if (
            run.status != "running"
            or run.cancel_requested_at is not None
            or job.lease_owner != worker
            or job.lease_token != token
            or job.lease_until is None
            or job.lease_until <= utcnow()
        ):
            return None
        return job, run

    def heartbeat(self, run_id: UUID, *, worker: str, token: int, duration: timedelta) -> bool:
        if duration <= timedelta(0):
            raise ValueError("lease duration must be positive")
        fenced = self._fenced(run_id, worker=worker, token=token)
        if fenced is None:
            return False
        job, _ = fenced
        now = utcnow()
        job.lease_until = now + duration
        job.heartbeat_at = now
        self.session.flush()
        return True

    def complete(
        self,
        run_id: UUID,
        *,
        worker: str,
        token: int,
        outcome: str,
        answer: dict[str, Any],
        coverage: dict[str, Any],
    ) -> bool:
        if outcome not in ("analysis", "safe_fallback", "no_evidence", "clarification"):
            raise ValueError("invalid outcome")
        fenced = self._fenced(run_id, worker=worker, token=token)
        if fenced is None:
            return False
        job, run = fenced
        run.status = "completed"
        run.outcome = outcome
        run.answer_json = answer
        run.coverage_json = coverage
        run.completed_at = utcnow()
        job.lease_owner = None
        job.lease_until = None
        self.session.flush()
        return True

    def request_cancel(self, run_id: UUID, *, owner_id: UUID) -> bool:
        # Порядок блокировок совпадает с захватом и завершением, исключая гонку отмены и публикации.
        job = self.session.scalar(
            select(AnalysisJob).where(AnalysisJob.run_id == run_id).with_for_update()
        )
        if job is None:
            return False
        run = self.session.scalar(
            select(AnalysisRun)
            .where(AnalysisRun.id == run_id, AnalysisRun.owner_user_id == owner_id)
            .with_for_update()
        )
        if run is None or run.status not in ("pending", "running"):
            return False
        run.cancel_requested_at = utcnow()
        self.session.flush()
        return True


class OutboxRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def enqueue(self, *, aggregate_id: UUID, kind: str, payload: dict[str, Any]) -> OutboxEvent:
        event = OutboxEvent(aggregate_id=aggregate_id, kind=kind, payload_json=payload)
        self.session.add(event)
        self.session.flush()
        return event

    def pending(self, consumer: str, *, limit: int = 100) -> list[OutboxEvent]:
        if not consumer or limit < 1 or limit > 1000:
            raise ValueError("invalid consumer or limit")
        return list(
            self.session.scalars(
                select(OutboxEvent)
                .outerjoin(
                    OutboxAck,
                    (OutboxAck.event_id == OutboxEvent.id) & (OutboxAck.consumer == consumer),
                )
                .where(OutboxAck.event_id.is_(None))
                .order_by(OutboxEvent.created_at, OutboxEvent.id)
                .limit(limit)
            )
        )

    def ack(self, event_id: UUID, *, consumer: str) -> None:
        if not consumer:
            raise ValueError("consumer is required")
        self.session.execute(
            insert(OutboxAck)
            .values(event_id=event_id, consumer=consumer)
            .on_conflict_do_nothing(index_elements=["event_id", "consumer"])
        )
