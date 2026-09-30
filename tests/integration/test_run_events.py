"""Durable run publication and replay invariants (PostgreSQL integration)."""

import os
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.domain.contracts import AnswerV1, PublicAnalysisV1
from app.services.analysis_run import ProgressCounts, StageProgress
from app.services.run_events import RunEventError, RunEventsService, append_progress
from app.storage.jobs import JobRepository
from app.storage.models import AnalysisRun, Conversation, IndexGeneration, RunEvent, User
from app.storage.repositories import OwnedRepository

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not configured"
)


@pytest.fixture
def engine():  # type: ignore[no-untyped-def]
    url = os.environ["TEST_DATABASE_URL"]
    admin = create_engine(url)
    schema = f"run_events_test_{uuid4().hex}"
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
def run(engine):  # type: ignore[no-untyped-def]
    owner, conversation, generation = uuid4(), uuid4(), uuid4()
    with Session(engine) as session, session.begin():
        session.add(User(id=owner, email_normalized=f"{owner}@example.test"))
        session.flush()
        session.add(Conversation(id=conversation, owner_user_id=owner))
        session.add(IndexGeneration(id=generation, config_versions_json={}))
        session.flush()
        saved, created = OwnedRepository(session).accept_run(
            owner_id=owner,
            conversation_id=conversation,
            expected_idea_version=0,
            content="query",
            query="query",
            idempotency_key="key",
            request_hash="a" * 64,
        )
        assert created
        return saved.id


def test_progress_write_is_fenced_and_sequence_is_durable(engine, run) -> None:  # type: ignore[no-untyped-def]
    with Session(engine) as session, session.begin():
        lease = JobRepository(session).claim_next(worker="worker", duration=timedelta(minutes=1))
        assert lease is not None
    update = StageProgress(
        attempt=1,
        stage="retrieving",
        phase="completed",
        stage_started_at=datetime.now(UTC),
        counts=ProgressCounts(feature_count=2, candidate_count=7),
    )
    with Session(engine) as session, session.begin():
        assert append_progress(session, run, worker="worker", token=lease.token, update=update)
    with Session(engine) as session, session.begin():
        assert not append_progress(session, run, worker="stale", token=lease.token, update=update)
    with Session(engine) as session:
        saved = session.get(AnalysisRun, run)
        events = list(
            session.scalars(
                select(RunEvent).where(RunEvent.run_id == run).order_by(RunEvent.sequence_no)
            )
        )
        assert saved is not None and saved.progress_json["counts"]["candidate_count"] == 7
        assert [event.sequence_no for event in events] == [1, 2]
        assert events[1].event_type == "retrieving"


def test_source_snapshot_and_event_rollback_together(engine, run) -> None:  # type: ignore[no-untyped-def]
    source_snapshot = {
        "schema_version": 1,
        "generation_id": None,
        "candidate_count": 0,
        "sources": [{"document_id": str(uuid4()), "title": "Verified source"}],
        "evidence": [],
    }
    with Session(engine) as session, session.begin():
        lease = JobRepository(session).claim_next(worker="worker", duration=timedelta(minutes=1))
        assert lease is not None
    with pytest.raises(RuntimeError):
        with Session(engine) as session, session.begin():
            assert JobRepository(session).save_evidence_snapshot(
                run,
                worker="worker",
                token=lease.token,
                snapshot=source_snapshot,
                evidence=[],
                coverage={"partial": True},
                generation_id=None,
            )
            raise RuntimeError("simulated crash before commit")
    with Session(engine) as session:
        saved = session.get(AnalysisRun, run)
        events = list(session.scalars(select(RunEvent).where(RunEvent.run_id == run)))
        assert saved is not None and saved.evidence_snapshot_json is None
        assert [event.event_type for event in events] == ["run_started"]
    with Session(engine) as session, session.begin():
        assert JobRepository(session).save_evidence_snapshot(
            run,
            worker="worker",
            token=lease.token,
            snapshot=source_snapshot,
            evidence=[],
            coverage={"partial": True},
            generation_id=None,
        )
    with Session(engine) as session:
        saved = session.get(AnalysisRun, run)
        events = list(session.scalars(select(RunEvent).where(RunEvent.run_id == run)))
        assert saved is not None and saved.evidence_snapshot_json == source_snapshot
        assert [event.event_type for event in events] == ["run_started", "sources_ready"]
        assert events[-1].payload_json["sources"] == source_snapshot["sources"]


def test_terminal_commit_replays_answer_without_regeneration_and_compacts(engine, run) -> None:  # type: ignore[no-untyped-def]
    text_value = "Проверенный ответ 🙂. " * 80
    digest = sha256(text_value.encode("utf-8")).hexdigest()
    presentation_id = sha256(("test-v1" + text_value).encode("utf-8")).hexdigest()
    presentation = {
        "schema_version": 1,
        "presentation_id": presentation_id,
        "renderer_version": "test-v1",
        "text": text_value,
        "text_sha256": digest,
        "chunk_count": (len(text_value) + 1023) // 1024,
    }
    with Session(engine) as session, session.begin():
        lease = JobRepository(session).claim_next(worker="worker", duration=timedelta(minutes=1))
        assert lease is not None
        answer = AnswerV1(
            summary=[], matches=[], differences=[], limitations=[], followup_suggestions=[]
        )
        public = PublicAnalysisV1(items=[], limitations=[])
        assert JobRepository(session).complete(
            run,
            worker="worker",
            token=lease.token,
            outcome="no_evidence",
            answer=answer.model_dump(mode="json"),
            coverage={},
            public_analysis=public.model_dump(mode="json"),
            answer_presentation=presentation,
        )
    with Session(engine) as session:
        events = RunEventsService(session).replay(run, cursor=0)
        assert [event.event_type for event in events][-6:] == [
            "verification",
            "analysis_summary",
            "answer_started",
            "answer_delta",
            "answer_delta",
            "completed",
        ]
        assert (
            "".join(event.payload["text"] for event in events if event.event_type == "answer_delta")
            == text_value
        )
        high_water = events[-1].sequence_no
    with Session(engine) as session, session.begin():
        removed = RunEventsService(session).compact(
            terminal_before=datetime.now(UTC) + timedelta(seconds=1)
        )
        assert removed == high_water
    with Session(engine) as session:
        replay = RunEventsService(session).replay(run, cursor=1)
        assert len(replay) == 1 and replay[0].event_type == "run_snapshot"
        assert replay[0].payload["high_water"] == high_water
        assert replay[0].payload["run"]["answer_presentation"]["text_sha256"] == digest


def test_cursor_beyond_high_water_is_rejected(engine, run) -> None:  # type: ignore[no-untyped-def]
    with Session(engine) as session:
        with pytest.raises(RunEventError):
            RunEventsService(session).replay(run, cursor=10)
