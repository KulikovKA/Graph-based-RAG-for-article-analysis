"""Постоянные аренды заданий, защита записей и подтверждения outbox по потребителям.

Методы работают в транзакции вызывающего кода; её фиксируют после записи всех
связанных строк. Токен аренды действует только до истечения её срока.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.storage.models import AnalysisJob, AnalysisRun, OutboxAck, OutboxEvent, RunEvidence, utcnow


@dataclass(frozen=True)
class JobLease:
    run_id: UUID
    worker: str
    token: int
    attempt: int


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

    def claim_next(self, *, worker: str, duration: timedelta) -> JobLease | None:
        """Claim the oldest ready job without relying on a volatile broker queue."""
        if not worker or len(worker) > 128 or duration <= timedelta(0):
            raise ValueError("invalid worker or lease duration")
        now = utcnow()
        job = self.session.scalar(
            select(AnalysisJob)
            .join(AnalysisRun, AnalysisRun.id == AnalysisJob.run_id)
            .where(
                AnalysisRun.status.in_(("pending", "running")),
                AnalysisJob.next_attempt_at <= now,
                or_(AnalysisJob.lease_until.is_(None), AnalysisJob.lease_until <= now),
            )
            .order_by(AnalysisJob.next_attempt_at, AnalysisRun.created_at, AnalysisJob.run_id)
            .with_for_update(of=AnalysisJob, skip_locked=True)
            .limit(1)
        )
        if job is None:
            return None
        run = self.session.scalar(
            select(AnalysisRun).where(AnalysisRun.id == job.run_id).with_for_update()
        )
        if run is None or run.status not in ("pending", "running"):
            return None
        if run.cancel_requested_at is not None:
            run.status = "cancelled"
            run.stage = "cancelled"
            run.completed_at = now
            job.lease_owner = None
            job.lease_until = None
            job.heartbeat_at = now
            from app.services.run_events import add_event

            add_event(
                self.session,
                run,
                "cancelled",
                {
                    "schema_version": 1,
                    "run": {
                        "id": str(run.id),
                        "status": run.status,
                        "stage": run.stage,
                        "error_code": None,
                    },
                },
            )
            self.session.flush()
            return None
        job.lease_token += 1
        job.attempts += 1
        job.lease_owner = worker
        job.lease_until = now + duration
        job.heartbeat_at = now
        run.status = "running"
        self.session.flush()
        return JobLease(run.id, worker, job.lease_token, job.attempts)

    def _fenced(
        self, run_id: UUID, *, worker: str, token: int
    ) -> tuple[AnalysisJob, AnalysisRun] | None:
        job = self.session.scalar(
            select(AnalysisJob)
            .where(AnalysisJob.run_id == run_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if job is None:
            return None
        run = self.session.scalar(
            select(AnalysisRun)
            .where(AnalysisRun.id == run_id)
            .with_for_update()
            .execution_options(populate_existing=True)
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

    def set_stage(self, run_id: UUID, *, worker: str, token: int, stage: str) -> bool:
        if not stage or len(stage) > 64:
            raise ValueError("invalid stage")
        fenced = self._fenced(run_id, worker=worker, token=token)
        if fenced is None:
            return False
        fenced[1].stage = stage
        self.session.flush()
        return True

    def update_config_versions(
        self, run_id: UUID, *, worker: str, token: int, patch: dict[str, Any]
    ) -> bool:
        fenced = self._fenced(run_id, worker=worker, token=token)
        if fenced is None:
            return False
        job_run = fenced[1]
        job_run.config_versions_json = {**job_run.config_versions_json, **patch}
        self.session.flush()
        return True

    def save_evidence_snapshot(
        self,
        run_id: UUID,
        *,
        worker: str,
        token: int,
        snapshot: dict[str, Any],
        evidence: list[dict[str, Any]],
        coverage: dict[str, Any],
        generation_id: UUID | None,
    ) -> bool:
        """Persist the immutable, packed input before any Analyst inference."""
        fenced = self._fenced(run_id, worker=worker, token=token)
        if fenced is None:
            return False
        run = fenced[1]
        if run.evidence_snapshot_json is not None:
            return False
        if len(evidence) > 36:
            raise ValueError("evidence pack exceeds the bounded evidence limit")
        if (
            self.session.scalar(
                select(RunEvidence.evidence_id).where(RunEvidence.run_id == run_id).limit(1)
            )
            is not None
        ):
            return False
        rows: list[RunEvidence] = []
        expected = {
            "evidence_id",
            "document_id",
            "revision_id",
            "chunk_id",
            "span_start",
            "span_end",
            "quoted_span",
            "source_url",
            "retrieval_score",
            "rerank_score",
            "index_generation_id",
        }
        for item in evidence:
            if set(item) != expected:
                raise ValueError("invalid evidence snapshot row")
            rows.append(RunEvidence(run_id=run_id, **item))
        run.evidence_snapshot_json = snapshot
        run.coverage_json = coverage
        run.index_generation_id = generation_id
        self.session.add_all(rows)
        self.session.flush()
        from app.services.run_events import add_event

        add_event(
            self.session,
            run,
            "sources_ready",
            {
                "schema_version": 1,
                "sources": snapshot.get("sources", []),
                "coverage": coverage,
            },
        )
        return True

    def fenced_run(self, run_id: UUID, *, worker: str, token: int) -> AnalysisRun | None:
        """Заблокировать job/run для составной записи в транзакции вызывающего сервиса."""
        fenced = self._fenced(run_id, worker=worker, token=token)
        return fenced[1] if fenced is not None else None

    def complete(
        self,
        run_id: UUID,
        *,
        worker: str,
        token: int,
        outcome: str,
        answer: dict[str, Any],
        coverage: dict[str, Any],
        analysis: dict[str, Any] | None = None,
        public_analysis: dict[str, Any] | None = None,
        answer_presentation: dict[str, Any] | None = None,
    ) -> bool:
        if outcome not in ("analysis", "safe_fallback", "no_evidence", "clarification"):
            raise ValueError("invalid outcome")
        fenced = self._fenced(run_id, worker=worker, token=token)
        if fenced is None:
            return False
        job, run = fenced
        if not run.legacy_projection and (
            public_analysis is None
            or answer_presentation is None
            or (outcome == "analysis" and analysis is None)
        ):
            raise ValueError("new publication contracts require verified result projections")
        if (public_analysis is None) != (answer_presentation is None) or (
            public_analysis is not None and outcome == "analysis" and analysis is None
        ):
            raise ValueError("result projections must be published as a verified bundle")
        run.status = "completed"
        run.stage = "completed"
        run.outcome = outcome
        run.answer_json = answer
        run.analysis_json = analysis
        run.public_analysis_json = public_analysis
        run.answer_presentation_json = answer_presentation
        run.coverage_json = coverage
        run.error_code = None
        run.completed_at = utcnow()
        if run.progress_json.get("stage") == "verification":
            run.progress_json = {**run.progress_json, "phase": "completed"}
        job.lease_owner = None
        job.lease_until = None
        if public_analysis is not None and answer_presentation is not None:
            from app.services.run_events import add_event, result_events, run_snapshot

            for event_type, payload in result_events(
                public_analysis=public_analysis or {},
                presentation=answer_presentation or {},
                outcome=outcome,
                run_snapshot=run_snapshot(run),
            ):
                add_event(self.session, run, event_type, payload)
        self.session.flush()
        return True

    def requeue(
        self,
        run_id: UUID,
        *,
        worker: str,
        token: int,
        delay: timedelta,
        reason_code: str = "RETRYABLE_FAILURE",
    ) -> bool:
        if delay < timedelta(0):
            raise ValueError("retry delay cannot be negative")
        fenced = self._fenced(run_id, worker=worker, token=token)
        if fenced is None:
            return False
        job, run = fenced
        run.status = "pending"
        run.stage = "accepted"
        job.lease_owner = None
        job.lease_until = None
        job.next_attempt_at = utcnow() + delay
        job.heartbeat_at = utcnow()
        run.progress_json = {
            "schema_version": 1,
            "attempt": job.attempts,
            "stage": "accepted",
            "phase": "waiting",
            "counts": {},
        }
        from app.services.run_events import add_event

        add_event(
            self.session,
            run,
            "run_requeued",
            {"schema_version": 1, "reason_code": reason_code, "progress": run.progress_json},
        )
        self.session.flush()
        return True

    def fail(
        self,
        run_id: UUID,
        *,
        worker: str,
        token: int,
        error_code: str,
    ) -> bool:
        if not error_code or len(error_code) > 128:
            raise ValueError("invalid error code")
        fenced = self._fenced(run_id, worker=worker, token=token)
        if fenced is None:
            return False
        job, run = fenced
        run.status = "failed"
        run.stage = "failed"
        run.error_code = error_code
        run.completed_at = utcnow()
        job.lease_owner = None
        job.lease_until = None
        job.heartbeat_at = utcnow()
        from app.services.run_events import add_event, run_snapshot

        add_event(
            self.session,
            run,
            "failed",
            {"schema_version": 1, "run": run_snapshot(run)},
        )
        self.session.flush()
        return True

    def finish_cancelled(self, run_id: UUID, *, worker: str, token: int) -> bool:
        """Finish only the current lease after a durable user cancel request."""
        job = self.session.scalar(
            select(AnalysisJob).where(AnalysisJob.run_id == run_id).with_for_update()
        )
        if job is None:
            return False
        run = self.session.scalar(
            select(AnalysisRun).where(AnalysisRun.id == run_id).with_for_update()
        )
        now = utcnow()
        if (
            run is None
            or run.status not in ("pending", "running")
            or run.cancel_requested_at is None
            or job.lease_owner != worker
            or job.lease_token != token
            or job.lease_until is None
            or job.lease_until <= now
        ):
            return False
        run.status = "cancelled"
        run.stage = "cancelled"
        run.completed_at = now
        job.lease_owner = None
        job.lease_until = None
        job.heartbeat_at = now
        from app.services.run_events import add_event, run_snapshot

        add_event(
            self.session,
            run,
            "cancelled",
            {"schema_version": 1, "run": run_snapshot(run)},
        )
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
