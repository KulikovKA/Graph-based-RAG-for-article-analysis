"""Проверка PostgreSQL; TEST_DATABASE_URL должен указывать на тестовую базу."""

import os
import time
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from tests.integration import test_repositories

from app.services.conversations import ConversationService
from app.services.memory import MemoryService
from app.storage.models import (
    Conversation,
    DocumentRevision,
    EvidenceChunk,
    IndexCatalog,
    IndexGeneration,
    Message,
    RunEvidence,
    SourceDocument,
    User,
)
from app.storage.repositories import OwnedRepository

pytestmark = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="no PostgreSQL test DB")
engine = test_repositories.engine


@pytest.fixture
def restart_engine():
    url = os.environ["TEST_DATABASE_URL"]
    admin = create_engine(url, pool_pre_ping=True)
    schema = f"repo_test_{uuid4().hex}"
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped_url = url + ("&" if "?" in url else "?") + f"options=-csearch_path%3D{schema}"
    scoped = create_engine(scoped_url, pool_pre_ping=True)
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


@pytest.mark.skipif(
    not os.getenv("TEST_POSTGRES_RESTART_DIR"), reason="перезапуск PostgreSQL не запрошен"
)
def test_history_and_summary_survive_postgres_server_restart(restart_engine):
    engine = restart_engine
    signal_dir = Path(os.environ["TEST_POSTGRES_RESTART_DIR"])
    if not signal_dir.is_dir() or any(signal_dir.iterdir()):
        raise ValueError("TEST_POSTGRES_RESTART_DIR должен указывать на пустую папку")
    owner = uuid4()
    with Session(engine) as session, session.begin():
        session.add(User(id=owner, email_normalized=f"{owner}@example.test"))
        session.flush()
        service = ConversationService(session)
        chat = service.create(owner).id
        message = service.append_message(owner, chat, role="user", content="durable").id
        service.set_summary(owner, chat, {"schema_version": 1, "text": "durable"}, message)
        started_before = session.scalar(text("SELECT pg_postmaster_start_time()"))
    engine.dispose()
    (signal_dir / "ready").write_text("ready", encoding="utf-8")
    deadline = time.monotonic() + 120
    while not (signal_dir / "continue").is_file():
        if time.monotonic() >= deadline:
            pytest.fail("Сигнал после перезапуска PostgreSQL не получен")
        time.sleep(0.2)
    with Session(engine) as session:
        started_after = session.scalar(text("SELECT pg_postmaster_start_time()"))
        assert started_after != started_before
        context = MemoryService(session).context(owner, chat)
        assert [item.id for item in context.recent] == [message]
        assert context.summary == {"schema_version": 1, "text": "durable"}
        assert context.summary_until_message_id == message


def test_restart_summary_ownership_and_stale_session(engine):
    owner, stranger = uuid4(), uuid4()
    with Session(engine) as session, session.begin():
        session.add_all(
            [
                User(id=owner, email_normalized=f"{owner}@example.test"),
                User(id=stranger, email_normalized=f"{stranger}@example.test"),
            ]
        )
        session.flush()
        conversations = ConversationService(session)
        chat = conversations.create(owner).id
        other = conversations.create(owner).id
        first = conversations.append_message(owner, chat, role="user", content="optical sensor").id
        last = conversations.append_message(owner, chat, role="user", content="latest").id
        session.get(Message, last).created_at = session.get(Message, first).created_at + timedelta(
            seconds=1
        )
        foreign = conversations.append_message(owner, other, role="user", content="foreign").id
        conversations.set_summary(owner, chat, {"legacy": True}, first)
    with Session(engine) as stale:
        cached = stale.get(Conversation, chat)
        assert cached is not None and cached.summary_until_message_id == first
        with Session(engine) as fresh, fresh.begin():
            MemoryService(fresh).rebuild_summary(owner, chat, until_message_id=last)
        assert cached.summary_until_message_id == first
        ConversationService(stale).set_summary(owner, chat, {"stale": True}, first)
        stale.commit()
    with Session(engine) as session:
        memory = MemoryService(session)
        context = memory.context(owner, chat, query="optical", recent_limit=1)
        assert [m.id for m in context.recent] == [last]
        assert [m.id for m in context.relevant] == [first]
        assert context.summary_until_message_id == last
        assert context.summary["schema_version"] == 1
        assert context.summary["builder_version"] == "extractive-v1"
        assert memory.context(owner, other, query="absent", recent_limit=0).recent == ()
        with pytest.raises(LookupError):
            memory.context(stranger, chat)
        with pytest.raises(LookupError):
            memory.rebuild_summary(owner, chat, until_message_id=foreign)


def test_concurrent_summaries_never_move_watermark_back(engine):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    owner = uuid4()
    with Session(engine) as session, session.begin():
        session.add(User(id=owner, email_normalized=f"{owner}@example.test"))
        session.flush()
        service = ConversationService(session)
        chat = service.create(owner).id
        first = service.append_message(owner, chat, role="user", content="first").id
        last = service.append_message(owner, chat, role="user", content="last").id
        session.get(Message, last).created_at = session.get(Message, first).created_at + timedelta(
            seconds=1
        )
    barrier = Barrier(2)

    def update(checkpoint):
        with Session(engine) as session, session.begin():
            barrier.wait(timeout=10)
            ConversationService(session).set_summary(
                owner, chat, {"checkpoint": str(checkpoint)}, checkpoint
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(update, checkpoint) for checkpoint in (first, last)]
        for future in futures:
            future.result(timeout=20)
    with Session(engine) as session:
        summary, checkpoint = ConversationService(session).summary(owner, chat)
        assert checkpoint == last
        assert summary == {"checkpoint": str(last)}


def test_historical_snapshot_survives_new_idea_and_generation(engine):
    owner, stranger = uuid4(), uuid4()
    with Session(engine) as session, session.begin():
        session.add_all(
            User(id=user, email_normalized=f"{user}@example.test") for user in (owner, stranger)
        )
        session.flush()
        service = ConversationService(session)
        chat = service.create(owner).id
        other_chat = service.create(owner).id
        repo = OwnedRepository(session)
        run, _ = repo.accept_run(
            owner_id=owner, conversation_id=chat, idempotency_key="first",
            request_hash="a" * 64, expected_idea_version=0, content="old", query="old",
        )
        first_version = repo.apply_idea_version(
            owner_id=owner, run_id=run.id, normalized={"features": ["old"]},
            state_hash="b" * 64,
        )
        old_generation = IndexGeneration(config_versions_json={"version": "old"})
        document = SourceDocument(
            source="fixture", external_id="one", canonical_url="https://example.test/one",
            kind="article", title="One",
        )
        session.add_all([old_generation, document])
        session.flush()
        catalog = session.get(IndexCatalog, 1)
        if catalog is None:
            catalog = IndexCatalog(id=1)
            session.add(catalog)
        catalog.current_generation_id = old_generation.id
        revision = DocumentRevision(
            document_id=document.id, content_hash="c" * 64, normalized_json={},
            ingest_state="normalized",
        )
        session.add(revision)
        session.flush()
        chunk = EvidenceChunk(
            revision_id=revision.id, section="abstract", ordinal=0, text="old text",
            section_start=0, section_end=8, hash="d" * 64, language="en",
        )
        session.add(chunk)
        session.flush()
        session.add(RunEvidence(
            run_id=run.id, document_id=document.id, revision_id=revision.id, chunk_id=chunk.id,
            span_start=0, span_end=8, quoted_span="old text", source_url=document.canonical_url,
            index_generation_id=old_generation.id,
        ))
        run.index_generation_id = old_generation.id
        run.evidence_snapshot_json = {"sources": [{"revision_id": str(revision.id)}]}
        run.legacy_projection = True
        run.status, run.outcome = "completed", "analysis"
        source_id, version_id, generation_id, revision_id = (
            run.id, first_version.id, old_generation.id, revision.id
        )
    with Session(engine) as session, session.begin():
        repo = OwnedRepository(session)
        new_run, _ = repo.accept_run(
            owner_id=owner, conversation_id=chat, idempotency_key="second",
            request_hash="e" * 64, expected_idea_version=1, content="new", query="new",
        )
        new_version = repo.apply_idea_version(
            owner_id=owner, run_id=new_run.id, normalized={"features": ["new"]},
            state_hash="f" * 64,
        )
        new_generation = IndexGeneration(config_versions_json={"version": "new"})
        session.add(new_generation)
        session.flush()
        session.get(IndexCatalog, 1).current_generation_id = new_generation.id
        assert new_version.id != version_id
        new_version_id = new_version.id
    engine.dispose()
    with Session(engine) as session:
        memory = MemoryService(session)
        historical = memory.historical(owner, chat, source_id)
        assert historical.idea_version.id == version_id
        assert historical.idea_version.normalized_json == {"features": ["old"]}
        assert historical.generation_id == generation_id
        assert historical.snapshot == {"sources": [{"revision_id": str(revision_id)}]}
        assert [(item.revision_id, item.quoted_span) for item in historical.evidence] == [
            (revision_id, "old text")
        ]
        assert memory.context(owner, chat).idea_version.id == new_version_id
        with pytest.raises(LookupError):
            memory.historical(stranger, chat, source_id)
        with pytest.raises(LookupError):
            memory.historical(owner, other_chat, source_id)
