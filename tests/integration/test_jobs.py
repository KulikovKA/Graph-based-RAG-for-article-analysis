"""Durable analysis queue, lease fencing, and verified result boundary."""

import asyncio
import os
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.domain.contracts import AnswerV1, CoverageV1
from app.domain.inference import InferenceCancelled, InferenceTimeout
from app.domain.planner import IdeaV1, PlannerV1
from app.services.analysis_run import (
    AnalysisRunConfig,
    AnalysisRunService,
    ProgressCounts,
    StageProgress,
    TerminalJobFailure,
)
from app.services.analyst import Analyst, AnalystResult
from app.services.evidence_pack import EvidencePack, EvidencePackItem
from app.services.idea_state import IdeaStateService
from app.storage.jobs import JobRepository
from app.storage.models import (
    AnalysisRun,
    Conversation,
    IndexCatalog,
    IndexGeneration,
    User,
)
from app.storage.repositories import OwnedRepository
from app.workers.analysis import AnalysisWorker, AnalysisWorkerConfig
from app.workers.inference import GenerationGate

postgres_only = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="no PostgreSQL test DB"
)


@pytest.fixture
def engine():  # type: ignore[no-untyped-def]
    url = os.environ["TEST_DATABASE_URL"]
    admin = create_engine(url)
    schema = f"jobs_test_{uuid4().hex}"
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped_url = url + ("&" if "?" in url else "?") + f"options=-csearch_path%3D{schema}"
    scoped = create_engine(scoped_url)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", scoped_url.replace("%", "%%"))
    try:
        command.upgrade(config, "head")
        yield scoped
    finally:
        scoped.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@pytest.fixture
def saved(engine):  # type: ignore[no-untyped-def]
    owner, conversation, generation = uuid4(), uuid4(), uuid4()
    with Session(engine) as session, session.begin():
        session.add(User(id=owner, email_normalized=f"{owner}@example.test"))
        session.flush()
        session.add(Conversation(id=conversation, owner_user_id=owner))
        session.add(IndexGeneration(id=generation, config_versions_json={}))
        session.flush()
        session.add(IndexCatalog(id=1, current_generation_id=generation))
        run, created = OwnedRepository(session).accept_run(
            owner_id=owner,
            conversation_id=conversation,
            expected_idea_version=0,
            content="fixture query",
            query="fixture query",
            idempotency_key="same-key",
            request_hash="a" * 64,
        )
        assert created
        return owner, conversation, generation, run.id


def _plan(intent: str = "new_idea", *, feature: str = "OCR") -> PlannerV1:
    return PlannerV1.model_validate(
        {
            "schema_version": 1,
            "intent": intent,
            "base_idea_version": 0,
            "add_features": (
                [{"text": feature, "rationale": "requested"}] if intent == "new_idea" else []
            ),
            "remove_feature_ids": [],
            "replace_features": [],
            "focus_evidence_ids": [],
            "suggested_retrieval": True,
            "confidence": 0.9,
        }
    )


def _service(analyst: Analyst) -> AnalysisRunService:
    return AnalysisRunService(
        cast(sessionmaker[Session], None),
        cast(Any, None),
        cast(Any, None),
        analyst,
        rerank=cast(Any, None),
        token_counter=lambda value: len(value),
        retrieval_config_hash="b" * 64,
        analyst_tokenizer_version="fixture-v1",
        config=AnalysisRunConfig(),
    )


def _fallback_fixture() -> tuple[Analyst, IdeaV1, EvidencePack, CoverageV1, AnalystResult]:
    feature_id, document_id, revision_id, chunk_id, evidence_id = (uuid4() for _ in range(5))
    idea = IdeaV1.model_validate(
        {
            "schema_version": 1,
            "domain": "vision",
            "features": [{"id": feature_id, "text": "OCR", "weight": 1.0}],
        }
    )
    item = EvidencePackItem(
        evidence_id=evidence_id,
        document_id=document_id,
        revision_id=revision_id,
        chunk_id=chunk_id,
        source="openalex",
        external_id="W123",
        canonical_url="https://example.test/source",
        title="Study",
        section="abstract",
        language="en",
        span_start=0,
        span_end=17,
        quoted_span="OCR is supported.",
        retrieval_score=1.0,
        rerank_score=1.0,
    )
    pack = EvidencePack((item,), 10, 6000)
    coverage = CoverageV1(sources=[], channels=[], partial=False, historical=False)
    analyst = Analyst(cast(Any, object()), model_id="fixture", prompt="{schema_json}\n{input_json}")
    result = analyst._fallback(idea, pack, coverage, 1, ("INFERENCE_ERROR",))
    return analyst, idea, pack, coverage, result


@postgres_only
def test_claim_retry_and_stale_worker_are_fenced(engine, saved) -> None:  # type: ignore[no-untyped-def]
    _owner, _conversation, _generation, run_id = saved
    with Session(engine) as session, session.begin():
        repo = JobRepository(session)
        first = repo.claim_next(worker="worker-a", duration=timedelta(seconds=30))
        assert first is not None and first.run_id == run_id
        assert first.attempt == 1 and first.token == 1
        assert repo.requeue(
            run_id,
            worker=first.worker,
            token=first.token,
            delay=timedelta(0),
        )

    with Session(engine) as session, session.begin():
        second = JobRepository(session).claim_next(
            worker="worker-b", duration=timedelta(seconds=30)
        )
        assert second is not None and second.run_id == run_id
        assert second.attempt == 2 and second.token == 2
        repo = JobRepository(session)
        assert not repo.set_stage(run_id, worker=first.worker, token=first.token, stage="analyzing")
        assert not repo.complete(
            run_id,
            worker=first.worker,
            token=first.token,
            outcome="analysis",
            answer={},
            coverage={},
        )
        assert repo.fail(
            run_id, worker=second.worker, token=second.token, error_code="FIXTURE_FAILED"
        )


@postgres_only
def test_planner_cas_and_evidence_snapshot_survive_restart(engine, saved) -> None:  # type: ignore[no-untyped-def]
    owner, _conversation, generation, run_id = saved
    empty_coverage = {"sources": [], "channels": [], "partial": False, "historical": False}
    snapshot = {
        "schema_version": 1,
        "generation_id": str(generation),
        "candidate_count": 0,
        "sources": [],
        "evidence": [],
    }
    with Session(engine) as session, session.begin():
        repo = JobRepository(session)
        first = repo.claim_next(worker="worker-a", duration=timedelta(seconds=30))
        assert first is not None
        applied = IdeaStateService(session).apply(
            owner_id=owner,
            run_id=run_id,
            worker=first.worker,
            lease_token=first.token,
            plan=_plan(feature="OCR"),
            generation_id=generation,
            retrieval_config_hash="b" * 64,
            query_hash="c" * 64,
        )
        assert applied.idea_version is not None
        version_id = applied.idea_version.id
        assert repo.save_evidence_snapshot(
            run_id,
            worker=first.worker,
            token=first.token,
            snapshot=snapshot,
            evidence=[],
            coverage=empty_coverage,
            generation_id=generation,
        )
        assert repo.requeue(run_id, worker=first.worker, token=first.token, delay=timedelta(0))

    with Session(engine) as session, session.begin():
        second = JobRepository(session).claim_next(
            worker="worker-b", duration=timedelta(seconds=30)
        )
        assert second is not None
        applied = IdeaStateService(session).apply(
            owner_id=owner,
            run_id=run_id,
            worker=second.worker,
            lease_token=second.token,
            plan=_plan(feature="A different patch"),
            generation_id=generation,
            retrieval_config_hash="b" * 64,
            query_hash="c" * 64,
        )
        assert applied.idea_version is not None and applied.idea_version.id == version_id
        run = session.get(AnalysisRun, run_id)
        assert run is not None
        assert run.evidence_snapshot_json == snapshot
        assert len(run.evidence_snapshot_json["sources"]) == 0
        assert not JobRepository(session).save_evidence_snapshot(
            run_id,
            worker=second.worker,
            token=second.token,
            snapshot={"schema_version": 1, "evidence": []},
            evidence=[],
            coverage=empty_coverage,
            generation_id=generation,
        )


@postgres_only
def test_idempotent_request_reuses_run_before_active_run_conflict(engine, saved) -> None:  # type: ignore[no-untyped-def]
    owner, conversation, _generation, run_id = saved
    with Session(engine) as session, session.begin():
        run, created = OwnedRepository(session).accept_run(
            owner_id=owner,
            conversation_id=conversation,
            expected_idea_version=0,
            content="fixture query",
            query="fixture query",
            idempotency_key="same-key",
            request_hash="a" * 64,
        )
        assert not created and run.id == run_id


@postgres_only
def test_cancel_request_wins_against_running_lease_and_pending_claim(engine, saved) -> None:  # type: ignore[no-untyped-def]
    owner, conversation, _generation, run_id = saved
    with Session(engine) as session, session.begin():
        lease = JobRepository(session).claim_next(worker="worker-a", duration=timedelta(seconds=30))
        assert lease is not None
        repo = JobRepository(session)
        assert repo.request_cancel(run_id, owner_id=owner)
        assert not repo.heartbeat(
            run_id, worker=lease.worker, token=lease.token, duration=timedelta(seconds=30)
        )
        assert repo.finish_cancelled(run_id, worker=lease.worker, token=lease.token)
        run = session.get(AnalysisRun, run_id)
        assert run is not None and run.status == "cancelled" and run.answer_json is None

    with Session(engine) as session, session.begin():
        new_run, created = OwnedRepository(session).accept_run(
            owner_id=owner,
            conversation_id=conversation,
            expected_idea_version=0,
            content="second request",
            query="second request",
            idempotency_key="second-key",
            request_hash="d" * 64,
        )
        assert created
        pending_id = new_run.id
        assert JobRepository(session).request_cancel(pending_id, owner_id=owner)
    with Session(engine) as session, session.begin():
        assert (
            JobRepository(session).claim_next(worker="worker-a", duration=timedelta(seconds=30))
            is None
        )
        run = session.get(AnalysisRun, pending_id)
        assert run is not None and run.status == "cancelled"


def test_validated_fallback_completes_and_invalid_fallback_is_rejected() -> None:
    analyst, idea, pack, coverage, fallback = _fallback_fixture()
    service = _service(analyst)
    verified = service._verify_result(fallback, idea=idea, pack=pack, coverage=coverage)
    assert verified.outcome == "safe_fallback"
    assert verified.answer.limitations[0].code == "safe_fallback"
    invalid = AnalystResult(
        outcome=fallback.outcome,
        analysis=None,
        answer=AnswerV1(
            summary=[], matches=[], differences=[], limitations=[], followup_suggestions=[]
        ),
        public_analysis=fallback.public_analysis,
        presentation=fallback.presentation,
        attempts=fallback.attempts,
    )
    with pytest.raises(TerminalJobFailure, match="INVALID_FALLBACK"):
        service._verify_result(invalid, idea=idea, pack=pack, coverage=coverage)


def test_analyst_timeout_uses_safe_excerpt_and_cancel_discards_late_response() -> None:
    analyst, idea, pack, coverage, _fallback = _fallback_fixture()

    class TimeoutProvider:
        async def complete_json(self, **_kwargs):  # type: ignore[no-untyped-def]
            raise InferenceTimeout("provider timed out after reasoning")

    timeout_analyst = Analyst(
        cast(Any, TimeoutProvider()), model_id="fixture", prompt="{schema_json}\n{input_json}"
    )
    result = asyncio.run(
        timeout_analyst.analyze(
            idea=idea, pack=pack, coverage=coverage, request_id="timeout", timeout=2
        )
    )
    assert result.outcome == "safe_fallback"
    assert "OCR is supported." in result.answer.summary[0].text
    _service(timeout_analyst)._verify_result(result, idea=idea, pack=pack, coverage=coverage)

    class WaitingProvider:
        def __init__(self) -> None:
            self.started = asyncio.Event()

        async def complete_json(self, *, cancel=None, **_kwargs):  # type: ignore[no-untyped-def]
            assert cancel is not None
            self.started.set()
            await cancel.wait()
            raise InferenceCancelled("cancelled")

    async def cancel_during_inference() -> None:
        provider = WaitingProvider()
        cancelling_analyst = Analyst(
            cast(Any, provider), model_id="fixture", prompt="{schema_json}\n{input_json}"
        )
        cancel = asyncio.Event()
        task = asyncio.create_task(
            cancelling_analyst.analyze(
                idea=idea,
                pack=pack,
                coverage=coverage,
                request_id="cancel",
                timeout=30,
                cancel=cancel,
            )
        )
        await asyncio.wait_for(provider.started.wait(), timeout=1)
        cancel.set()
        with pytest.raises(InferenceCancelled):
            await task

    asyncio.run(cancel_during_inference())


def test_progress_callback_does_not_require_sse_transport() -> None:
    update = StageProgress(
        attempt=1,
        stage="retrieving",
        phase="completed",
        stage_started_at=datetime.now(UTC),
        counts=ProgressCounts(feature_count=3, candidate_count=12),
    )
    assert update.counts.candidate_count == 12
    assert update.counts.selected_document_count is None
    assert update.phase == "completed"


@pytest.mark.parametrize("cancel_phase", ["load", "reasoning", "final_output"])
def test_generation_slot_waits_for_backend_stop_before_reuse(cancel_phase: str) -> None:
    async def scenario() -> None:
        gate = GenerationGate(stop_grace=1)
        cancel = asyncio.Event()
        backend_stopped = asyncio.Event()
        stop_requested = asyncio.Event()
        phase_started = asyncio.Event()
        second_started = asyncio.Event()

        async def generation() -> str:
            try:
                for phase in ("load", "reasoning", "final_output"):
                    if phase == cancel_phase:
                        phase_started.set()
                        await asyncio.Event().wait()
                    await asyncio.sleep(0)
                return "too late"
            except asyncio.CancelledError:
                stop_requested.set()
                await backend_stopped.wait()
                raise

        first = asyncio.create_task(gate.run(generation, timeout=5, cancel=cancel))
        await asyncio.wait_for(phase_started.wait(), timeout=1)
        cancel.set()
        await asyncio.wait_for(stop_requested.wait(), timeout=1)

        async def second_generation() -> str:
            second_started.set()
            return "next"

        second = asyncio.create_task(gate.run(second_generation, timeout=5))
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(second_started.wait(), timeout=0.02)
        backend_stopped.set()
        with pytest.raises(InferenceCancelled):
            await first
        assert await asyncio.wait_for(second, timeout=1) == "next"
        assert second_started.is_set()

    asyncio.run(scenario())


def test_cancel_during_analyst_repair_propagates_without_fallback() -> None:
    analyst, idea, pack, coverage, _fallback = _fallback_fixture()

    class RepairProvider:
        def __init__(self) -> None:
            self.calls = 0
            self.repair_started = asyncio.Event()

        async def complete_json(self, *, cancel=None, **_kwargs):  # type: ignore[no-untyped-def]
            self.calls += 1
            if self.calls == 1:
                return SimpleNamespace(value={"schema_version": 1, "bad": True}, metadata=None)
            assert cancel is not None
            self.repair_started.set()
            await cancel.wait()
            raise InferenceCancelled("repair cancelled")

    async def scenario() -> None:
        provider = RepairProvider()
        repairing = Analyst(
            cast(Any, provider), model_id="fixture", prompt="{schema_json}\n{input_json}"
        )
        cancel = asyncio.Event()
        task = asyncio.create_task(
            repairing.analyze(
                idea=idea, pack=pack, coverage=coverage, request_id="repair",
                timeout=5, cancel=cancel,
            )
        )
        await asyncio.wait_for(provider.repair_started.wait(), timeout=1)
        cancel.set()
        with pytest.raises(InferenceCancelled):
            await task
        assert provider.calls == 2

    asyncio.run(scenario())


@postgres_only
def test_worker_discards_late_result_after_durable_cancel(engine, saved) -> None:  # type: ignore[no-untyped-def]
    owner, _conversation, _generation, run_id = saved

    class LateService:
        def __init__(self) -> None:
            self.started = asyncio.Event()
            self.returning_late_result = asyncio.Event()

        async def execute(self, _run_id, *, cancel, **_kwargs):  # type: ignore[no-untyped-def]
            self.started.set()
            await cancel.wait()
            self.returning_late_result.set()
            return object()

    async def scenario() -> None:
        service = LateService()
        factory = sessionmaker(engine, class_=Session, expire_on_commit=False)
        worker = AnalysisWorker(
            factory,
            cast(AnalysisRunService, service),
            config=AnalysisWorkerConfig(
                worker_id="late-worker", lease_seconds=1, heartbeat_seconds=0.01,
                poll_seconds=0.01,
            ),
        )
        task = asyncio.create_task(worker.run_once())
        await asyncio.wait_for(service.started.wait(), timeout=1)
        with Session(engine) as session, session.begin():
            assert JobRepository(session).request_cancel(run_id, owner_id=owner)
        assert await asyncio.wait_for(task, timeout=2)
        assert service.returning_late_result.is_set()

    asyncio.run(scenario())
    with Session(engine) as session:
        run = session.get(AnalysisRun, run_id)
        assert run is not None and run.status == "cancelled" and run.answer_json is None
