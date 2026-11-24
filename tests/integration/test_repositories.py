"""Проверки транзакционных инвариантов репозиториев в изолированной схеме PostgreSQL."""

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, delete, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.services.conversations import ConversationService
from app.storage import jobs
from app.storage.jobs import JobRepository, OutboxRepository
from app.storage.models import (
    AnalysisJob,
    AnalysisRun,
    Conversation,
    DocumentRevision,
    EvidenceChunk,
    RunEvidence,
    SourceDocument,
    User,
)
from app.storage.repositories import IdempotencyConflict, OwnedRepository, VersionConflict

pytestmark = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="no PostgreSQL test DB")


@pytest.fixture
def engine():  # type: ignore[no-untyped-def]
    url = os.environ["TEST_DATABASE_URL"]
    admin = create_engine(url)
    schema = f"repo_test_{uuid4().hex}"
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


def test_owner_idempotency_version_and_fencing(engine) -> None:  # type: ignore[no-untyped-def]
    owner, stranger, conversation_id = uuid4(), uuid4(), uuid4()
    with Session(engine) as session, session.begin():
        session.add_all(
            [
                User(id=owner, email_normalized=f"{owner}@example.test"),
                User(id=stranger, email_normalized=f"{stranger}@example.test"),
            ]
        )
        session.flush()
        session.add(Conversation(id=conversation_id, owner_user_id=owner))
    with Session(engine) as session, session.begin():
        repo = OwnedRepository(session)
        run, created = repo.accept_run(
            owner_id=owner,
            conversation_id=conversation_id,
            idempotency_key="k",
            request_hash="a" * 64,
            expected_idea_version=0,
            content="idea",
            query="idea",
        )
        assert created
        # Keep this fencing test focused on the legacy repository completion contract.
        run.legacy_projection = True
        run_id, message_id = run.id, run.message_id
    with Session(engine) as session, session.begin():
        repo = OwnedRepository(session)
        same, created = repo.accept_run(
            owner_id=owner,
            conversation_id=conversation_id,
            idempotency_key="k",
            request_hash="a" * 64,
            expected_idea_version=999,
            content="ignored",
            query="ignored",
        )
        assert not created and same.id == run_id
        assert repo.get_run(run_id, owner_id=stranger) is None
        assert repo.get_message(message_id, owner_id=stranger) is None
        assert repo.evidence(run_id, owner_id=stranger) == []
        with pytest.raises(LookupError):
            repo.accept_run(
                owner_id=stranger,
                conversation_id=conversation_id,
                idempotency_key="k",
                request_hash="a" * 64,
                expected_idea_version=0,
                content="x",
                query="x",
            )
        with pytest.raises(IdempotencyConflict):
            repo.accept_run(
                owner_id=owner,
                conversation_id=conversation_id,
                idempotency_key="k",
                request_hash="b" * 64,
                expected_idea_version=0,
                content="x",
                query="x",
            )
    with Session(engine) as session, session.begin():
        repo = OwnedRepository(session)
        version = repo.apply_idea_version(
            owner_id=owner, run_id=run_id, normalized={"features": []}, state_hash="c" * 64
        )
        assert version.version_no == 1
        assert (
            repo.apply_idea_version(
                owner_id=owner, run_id=run_id, normalized={"features": [1]}, state_hash="d" * 64
            ).id
            == version.id
        )
        assert (
            JobRepository(session).claim(run_id, worker="old", duration=timedelta(seconds=30)) == 1
        )
    with Session(engine) as session, session.begin():
        job = JobRepository(session)
        assert job.claim(run_id, worker="new", duration=timedelta(seconds=30)) is None
        assert not job.complete(
            run_id, worker="new", token=1, outcome="analysis", answer={}, coverage={}
        )
        assert not job.complete(
            run_id, worker="old", token=0, outcome="analysis", answer={}, coverage={}
        )
        lease = session.get(AnalysisJob, run_id)
        assert lease is not None
        lease.lease_until = session.scalar(
            select(func.statement_timestamp() - timedelta(seconds=1))
        )
    with Session(engine) as session, session.begin():
        job = JobRepository(session)
        assert job.claim(run_id, worker="new", duration=timedelta(seconds=30)) == 2
        assert not job.complete(
            run_id, worker="old", token=1, outcome="analysis", answer={}, coverage={}
        )
        assert job.complete(
            run_id, worker="new", token=2, outcome="analysis", answer={}, coverage={}
        )
        assert not job.complete(
            run_id, worker="new", token=2, outcome="analysis", answer={}, coverage={}
        )
    with Session(engine) as session, session.begin():
        with pytest.raises(VersionConflict):
            OwnedRepository(session).accept_run(
                owner_id=owner,
                conversation_id=conversation_id,
                idempotency_key="k2",
                request_hash="e" * 64,
                expected_idea_version=0,
                content="x",
                query="x",
            )


@pytest.mark.parametrize("skew", [-3, 3])
def test_queue_uses_database_time_under_worker_clock_skew(engine, monkeypatch, skew) -> None:  # type: ignore[no-untyped-def]
    owner, conversation_id = uuid4(), uuid4()
    monkeypatch.setattr(
        jobs, "utcnow", lambda: datetime.now(UTC) + timedelta(hours=skew), raising=False
    )
    duration = timedelta(minutes=1)
    with Session(engine) as session, session.begin():
        session.execute(text("SET LOCAL TIME ZONE 'Asia/Tokyo'"))
        session.add(User(id=owner, email_normalized=f"{owner}@example.test"))
        session.flush()
        session.add(Conversation(id=conversation_id, owner_user_id=owner))
        session.flush()
        run, _ = OwnedRepository(session).accept_run(
            owner_id=owner,
            conversation_id=conversation_id,
            idempotency_key="clock-test",
            request_hash="a" * 64,
            expected_idea_version=0,
            content="fixture",
            query="fixture",
        )
        run_id = run.id
        queue = JobRepository(session)
        lease = queue.claim_next(worker="first", duration=duration)
        assert lease is not None and lease.run_id == run_id and lease.token == 1
        job = session.get(AnalysisJob, run_id)
        assert job is not None
        before = session.scalar(select(func.statement_timestamp()))
        assert before is not None and job.heartbeat_at is not None
        assert job.next_attempt_at <= job.heartbeat_at <= before
        assert job.heartbeat_at.utcoffset() == timedelta(hours=9)
        assert queue.heartbeat(run_id, worker="first", token=1, duration=duration)
        assert job.heartbeat_at >= before and job.lease_until == job.heartbeat_at + duration
        assert job.heartbeat_at.utcoffset() == timedelta(0)

        # Значение ещё в будущем относительно now() транзакции, но уже истекло.
        job.lease_until = session.scalar(select(func.statement_timestamp()))
        session.flush()
        assert not queue.heartbeat(run_id, worker="first", token=1, duration=duration)
        assert not queue.set_stage(run_id, worker="first", token=1, stage="late")
        assert queue.claim(run_id, worker="second", duration=duration) == 2
        assert not queue.set_stage(run_id, worker="first", token=1, stage="fenced")

        assert queue.requeue(run_id, worker="second", token=2, delay=duration)
        assert job.next_attempt_at == job.heartbeat_at + duration
        assert queue.claim_next(worker="third", duration=duration) is None
        job.next_attempt_at = session.scalar(select(func.statement_timestamp()))
        session.flush()
        new_lease = queue.claim_next(worker="third", duration=duration)
        assert new_lease is not None and new_lease.token == 3

        assert queue.request_cancel(run_id, owner_id=owner)
        assert not queue.heartbeat(run_id, worker="third", token=3, duration=duration)
        assert not queue.finish_cancelled(run_id, worker="second", token=2)
        assert queue.finish_cancelled(run_id, worker="third", token=3)
        ended = session.get(AnalysisRun, run_id)
        assert ended is not None and ended.status == "cancelled"
        assert ended.completed_at is not None and ended.cancel_requested_at is not None
        assert before <= ended.cancel_requested_at <= ended.completed_at
        assert ended.completed_at == job.heartbeat_at and job.lease_until is None


def test_outbox_ack_and_referenced_chunk(engine) -> None:  # type: ignore[no-untyped-def]
    owner, conversation_id = uuid4(), uuid4()
    with Session(engine) as session, session.begin():
        session.add(User(id=owner, email_normalized=f"{owner}@example.test"))
        session.flush()
        session.add(Conversation(id=conversation_id, owner_user_id=owner))
        session.flush()
        run, _ = OwnedRepository(session).accept_run(
            owner_id=owner,
            conversation_id=conversation_id,
            idempotency_key="k",
            request_hash="a" * 64,
            expected_idea_version=0,
            content="q",
            query="q",
        )
        document = SourceDocument(
            source="fixture",
            external_id="one",
            canonical_url="https://example.test/one",
            kind="article",
            title="One",
        )
        session.add(document)
        session.flush()
        revision = DocumentRevision(
            document_id=document.id,
            content_hash="b" * 64,
            normalized_json={},
            ingest_state="normalized",
        )
        session.add(revision)
        session.flush()
        chunk = EvidenceChunk(
            revision_id=revision.id,
            section="abstract",
            ordinal=0,
            text="quoted",
            section_start=0,
            section_end=6,
            hash="c" * 64,
            language="en",
        )
        session.add(chunk)
        session.flush()
        session.add(
            RunEvidence(
                run_id=run.id,
                document_id=document.id,
                revision_id=revision.id,
                chunk_id=chunk.id,
                span_start=0,
                span_end=6,
                quoted_span="quoted",
                source_url=document.canonical_url,
            )
        )
        event = OutboxRepository(session).enqueue(
            aggregate_id=revision.id,
            kind="revision.ready",
            payload={"revision_id": str(revision.id)},
        )
        event_id, chunk_id = event.id, chunk.id
    with Session(engine) as session, session.begin():
        outbox = OutboxRepository(session)
        assert [e.id for e in outbox.pending("qdrant")] == [event_id]
        outbox.ack(event_id, consumer="qdrant")
        outbox.ack(event_id, consumer="qdrant")
        assert outbox.pending("qdrant") == []
        assert [e.id for e in outbox.pending("graph")] == [event_id]
    with pytest.raises(IntegrityError), Session(engine) as session, session.begin():
        session.execute(delete(EvidenceChunk).where(EvidenceChunk.id == chunk_id))


def test_conversation_memory_is_durable_and_owner_scoped(engine) -> None:  # type: ignore[no-untyped-def]
    owner, stranger = uuid4(), uuid4()
    with Session(engine) as session, session.begin():
        session.add_all(
            [
                User(id=owner, email_normalized=f"{owner}@example.test"),
                User(id=stranger, email_normalized=f"{stranger}@example.test"),
            ]
        )
        session.flush()
        service = ConversationService(session)
        conversation = service.create(owner, title="Durable")
        conversation_id = conversation.id
        run, _ = OwnedRepository(session).accept_run(
            owner_id=owner,
            conversation_id=conversation_id,
            idempotency_key="memory-1",
            request_hash="a" * 64,
            expected_idea_version=0,
            content="idea",
            query="query",
        )
        version = OwnedRepository(session).apply_idea_version(
            owner_id=owner,
            run_id=run.id,
            normalized={"schema_version": 1, "features": [{"id": "f1", "text": "old"}]},
            state_hash="b" * 64,
        )
        version_id = version.id
        message_id = run.message_id

    with Session(engine) as session, session.begin():
        service = ConversationService(session)
        assert [item.id for item in service.list_conversations(owner)] == [conversation_id]
        assert [item.id for item in service.messages(owner, conversation_id)] == [message_id]
        assert [item.id for item in service.idea_versions(owner, conversation_id)] == [version_id]
        service.set_summary(owner, conversation_id, {"topics": ["idea"]}, message_id)
        assert service.summary(owner, conversation_id) == (
            {"topics": ["idea"]},
            message_id,
        )
        assert service.list_conversations(stranger) == []
        with pytest.raises(LookupError):
            service.get(stranger, conversation_id)
        with pytest.raises(LookupError):
            service.set_summary(stranger, conversation_id, {}, message_id)
