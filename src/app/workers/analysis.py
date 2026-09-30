"""Durable polling worker for analysis jobs."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.inference import InferenceCancelled
from app.services.analysis_run import (
    AnalysisRunService,
    LeaseLost,
    ProgressCallback,
    RetryableJobFailure,
    RunCancelled,
    StageProgress,
    TerminalJobFailure,
)
from app.services.run_events import append_progress
from app.storage.jobs import JobLease, JobRepository
from app.storage.models import AnalysisRun

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnalysisWorkerConfig:
    worker_id: str = "analysis-worker-1"
    lease_seconds: float = 30
    heartbeat_seconds: float = 5
    poll_seconds: float = 1
    max_attempts: int = 3
    retry_base_seconds: float = 2
    retry_max_seconds: float = 30

    def __post_init__(self) -> None:
        if not self.worker_id or len(self.worker_id) > 128:
            raise ValueError("invalid worker id")
        if self.lease_seconds <= 0 or not 0 < self.heartbeat_seconds < self.lease_seconds:
            raise ValueError("heartbeat must be shorter than the positive lease")
        if self.poll_seconds <= 0 or self.max_attempts < 1:
            raise ValueError("invalid poll interval or retry limit")
        if self.retry_base_seconds < 0 or self.retry_max_seconds < self.retry_base_seconds:
            raise ValueError("invalid retry backoff")


class AnalysisWorker:
    """One sequential consumer; PostgreSQL remains the source of durable work."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        service: AnalysisRunService,
        *,
        config: AnalysisWorkerConfig | None = None,
        progress: ProgressCallback | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.service = service
        self.config = config or AnalysisWorkerConfig()
        self.progress = progress
        self._stop = asyncio.Event()

    def stop(self) -> None:
        self._stop.set()

    async def run_forever(self) -> None:
        while not self._stop.is_set():
            if await self.run_once():
                continue
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.config.poll_seconds)
            except TimeoutError:
                pass

    async def run_once(self) -> bool:
        lease = self._claim()
        if lease is None:
            return False
        cancel = asyncio.Event()
        heartbeat = asyncio.create_task(self._maintain_lease(lease, cancel))
        try:
            result = await self.service.execute(
                lease.run_id,
                worker=lease.worker,
                lease_token=lease.token,
                attempt=lease.attempt,
                cancel=cancel,
                progress=lambda update: self._persist_progress(lease, update),
            )
            if cancel.is_set():
                self._finish_cancelled(lease)
                return True
            committed = self._complete(lease, result)
            if not committed:
                # A cancel request that won before the terminal transaction is final.
                self._finish_cancelled(lease)
            return True
        except (RunCancelled, InferenceCancelled):
            self._finish_cancelled(lease)
            return True
        except LeaseLost:
            # Late responses from a stale lease are discarded without changing the run.
            self._finish_cancelled(lease)
            logger.info("analysis_job_lease_lost", extra={"run_id": str(lease.run_id)})
            return True
        except RetryableJobFailure as exc:
            self._retry_or_fail(lease, exc.error_code)
            return True
        except TerminalJobFailure as exc:
            self._fail(lease, exc.error_code)
            return True
        except asyncio.CancelledError:
            # Backend cancellation is awaited inside its generation gate; leave an interrupted
            # lease recoverable if the process itself is shutting down.
            cancel.set()
            raise
        except Exception:
            # Unexpected stage errors get a bounded retry, with no prompt/provider body in logs.
            logger.error("analysis_job_unexpected_error", extra={"run_id": str(lease.run_id)})
            self._retry_or_fail(lease, "WORKER_ERROR")
            return True
        finally:
            heartbeat.cancel()
            try:
                await heartbeat
            except asyncio.CancelledError:
                pass

    def _claim(self) -> JobLease | None:
        with self.session_factory() as session, session.begin():
            return JobRepository(session).claim_next(
                worker=self.config.worker_id,
                duration=timedelta(seconds=self.config.lease_seconds),
            )

    async def _maintain_lease(self, lease: JobLease, cancel: asyncio.Event) -> None:
        while True:
            await asyncio.sleep(self.config.heartbeat_seconds)
            renewed = await asyncio.to_thread(self._heartbeat, lease)
            if not renewed:
                cancel.set()
                return

    def _heartbeat(self, lease: JobLease) -> bool:
        with self.session_factory() as session, session.begin():
            return JobRepository(session).heartbeat(
                lease.run_id,
                worker=lease.worker,
                token=lease.token,
                duration=timedelta(seconds=self.config.lease_seconds),
            )

    def _complete(self, lease: JobLease, result: object) -> bool:
        outcome = getattr(result, "outcome", None)
        answer = getattr(result, "answer", None)
        analysis = getattr(result, "analysis", None)
        public_analysis = getattr(result, "public_analysis", None)
        answer_presentation = getattr(result, "presentation", None)
        if outcome not in ("analysis", "safe_fallback", "no_evidence", "clarification"):
            raise TerminalJobFailure("INVALID_ANALYST_RESULT")
        if answer is None or not callable(getattr(answer, "model_dump", None)):
            raise TerminalJobFailure("INVALID_ANALYST_RESULT")
        projections = {
            "answer": answer.model_dump(mode="json"),
            "analysis": analysis.model_dump(mode="json") if analysis is not None else None,
            "public_analysis": (
                public_analysis.model_dump(mode="json") if public_analysis is not None else None
            ),
            "answer_presentation": (
                answer_presentation.model_dump(mode="json")
                if answer_presentation is not None
                else None
            ),
        }
        try:
            with self.session_factory() as session, session.begin():
                coverage = session.scalar(
                    select(AnalysisRun.coverage_json).where(AnalysisRun.id == lease.run_id)
                )
                if coverage is None:
                    return False
                return JobRepository(session).complete(
                    lease.run_id,
                    worker=lease.worker,
                    token=lease.token,
                    outcome=outcome,
                    answer=projections["answer"],
                    coverage=coverage,
                    analysis=projections["analysis"],
                    public_analysis=projections["public_analysis"],
                    answer_presentation=projections["answer_presentation"],
                )
        except Exception:
            # Resolve an unknown COMMIT outcome before the worker loop can retry inference.
            try:
                with self.session_factory() as session:
                    saved = session.get(AnalysisRun, lease.run_id)
                    if (
                        saved is not None
                        and saved.status == "completed"
                        and saved.outcome == outcome
                        and saved.answer_json == projections["answer"]
                        and saved.analysis_json == projections["analysis"]
                        and saved.public_analysis_json == projections["public_analysis"]
                        and saved.answer_presentation_json == projections["answer_presentation"]
                    ):
                        return True
            except Exception:
                pass
            raise

    async def _persist_progress(self, lease: JobLease, update: StageProgress) -> None:
        with self.session_factory() as session, session.begin():
            persisted = append_progress(
                session,
                lease.run_id,
                worker=lease.worker,
                token=lease.token,
                update=update,
            )
        if not persisted:
            raise LeaseLost("lease lost while persisting progress")
        if self.progress is not None:
            await self.progress(update)

    def _finish_cancelled(self, lease: JobLease) -> bool:
        with self.session_factory() as session, session.begin():
            return JobRepository(session).finish_cancelled(
                lease.run_id, worker=lease.worker, token=lease.token
            )

    def _retry_or_fail(self, lease: JobLease, error_code: str) -> None:
        if lease.attempt >= self.config.max_attempts:
            self._fail(lease, error_code)
            return
        delay = min(
            self.config.retry_base_seconds * (2 ** max(0, lease.attempt - 1)),
            self.config.retry_max_seconds,
        )
        with self.session_factory() as session, session.begin():
            requeued = JobRepository(session).requeue(
                lease.run_id,
                worker=lease.worker,
                token=lease.token,
                delay=timedelta(seconds=delay),
                reason_code=error_code,
            )
        if requeued:
            logger.warning(
                "analysis_job_requeued",
                extra={
                    "run_id": str(lease.run_id),
                    "error_code": error_code,
                    "attempt": lease.attempt,
                },
            )
        else:
            self._finish_cancelled(lease)

    def _fail(self, lease: JobLease, error_code: str) -> None:
        with self.session_factory() as session, session.begin():
            failed = JobRepository(session).fail(
                lease.run_id,
                worker=lease.worker,
                token=lease.token,
                error_code=error_code,
            )
        if failed:
            logger.error(
                "analysis_job_failed",
                extra={
                    "run_id": str(lease.run_id),
                    "error_code": error_code,
                    "attempt": lease.attempt,
                },
            )
        else:
            self._finish_cancelled(lease)
