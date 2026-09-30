"""Проверки миграций и ограничений PostgreSQL в изолированной схеме."""

import os
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.storage.models import (
    AnalysisRun,
    Conversation,
    DocumentRevision,
    EvidenceChunk,
    Message,
    RunEvidence,
    SourceDocument,
    User,
)

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not configured")


def _alembic_config(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def test_migrations_round_trip_and_database_invariants() -> None:
    assert TEST_DATABASE_URL is not None
    admin_engine = create_engine(TEST_DATABASE_URL)
    schema = f"db_test_{uuid4().hex}"
    with admin_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    scoped_url = (
        TEST_DATABASE_URL
        + ("&" if "?" in TEST_DATABASE_URL else "?")
        + f"options=-csearch_path%3D{schema}"
    )
    engine = create_engine(scoped_url)
    config = _alembic_config(scoped_url)
    try:
        command.upgrade(config, "head")
        with engine.connect() as connection:
            tables = set(
                connection.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname = current_schema()")
                ).scalars()
            )
        assert {
            "users",
            "analysis_runs",
            "run_evidence",
            "graph_facts",
            "index_generations",
        } <= tables

        owner_id, other_owner_id, conversation_id = uuid4(), uuid4(), uuid4()
        message_id = uuid4()
        run_id, second_run_id = uuid4(), uuid4()
        document_one, document_two = uuid4(), uuid4()
        revision_one, revision_two, chunk_one = uuid4(), uuid4(), uuid4()
        with Session(engine) as session, session.begin():
            session.add_all(
                [
                    User(id=owner_id, email_normalized=f"{owner_id}@example.test"),
                    User(
                        id=other_owner_id,
                        email_normalized=f"{other_owner_id}@example.test",
                    ),
                ]
            )
            session.flush()
            session.add_all(
                [
                    Conversation(id=conversation_id, owner_user_id=owner_id),
                    SourceDocument(
                        id=document_one,
                        source="fixture",
                        external_id="one",
                        canonical_url="https://example.test/one",
                        kind="article",
                        title="One",
                    ),
                    SourceDocument(
                        id=document_two,
                        source="fixture",
                        external_id="two",
                        canonical_url="https://example.test/two",
                        kind="article",
                        title="Two",
                    ),
                ]
            )
            session.flush()
            session.add_all(
                [
                    Message(
                        id=message_id,
                        conversation_id=conversation_id,
                        role="user",
                        content="query",
                    ),
                    DocumentRevision(
                        id=revision_one,
                        document_id=document_one,
                        content_hash="1" * 64,
                        normalized_json={},
                        ingest_state="normalized",
                    ),
                    DocumentRevision(
                        id=revision_two,
                        document_id=document_two,
                        content_hash="2" * 64,
                        normalized_json={},
                        ingest_state="normalized",
                    ),
                ]
            )
            session.flush()
            session.add(
                EvidenceChunk(
                    id=chunk_one,
                    revision_id=revision_one,
                    section="abstract",
                    ordinal=0,
                    text="evidence",
                    section_start=0,
                    section_end=8,
                    hash="3" * 64,
                    language="en",
                )
            )
            session.flush()
            session.add(
                AnalysisRun(
                    id=run_id,
                    conversation_id=conversation_id,
                    owner_user_id=owner_id,
                    message_id=message_id,
                    expected_idea_version=0,
                    status="pending",
                    stage="accepted",
                    query="query",
                    coverage_json={},
                    config_versions_json={},
                    event_seq_high_water=0,
                    idempotency_key="request-1",
                    request_hash="a" * 64,
                )
            )

        with pytest.raises(IntegrityError), Session(engine) as session, session.begin():
            session.add(
                AnalysisRun(
                    id=second_run_id,
                    conversation_id=conversation_id,
                    owner_user_id=owner_id,
                    message_id=message_id,
                    expected_idea_version=0,
                    status="running",
                    stage="accepted",
                    query="query",
                    coverage_json={},
                    config_versions_json={},
                    event_seq_high_water=0,
                    idempotency_key="request-2",
                    request_hash="b" * 64,
                )
            )

        with Session(engine) as session, session.begin():
            session.get(AnalysisRun, run_id).status = "completed"
            session.get(AnalysisRun, run_id).outcome = "analysis"

        with pytest.raises(IntegrityError), Session(engine) as session, session.begin():
            session.add(
                AnalysisRun(
                    id=second_run_id,
                    conversation_id=conversation_id,
                    owner_user_id=owner_id,
                    message_id=message_id,
                    expected_idea_version=0,
                    status="completed",
                    stage="done",
                    outcome="analysis",
                    query="query",
                    coverage_json={},
                    config_versions_json={},
                    event_seq_high_water=0,
                    idempotency_key="request-1",
                    request_hash="c" * 64,
                )
            )

        with pytest.raises(IntegrityError), Session(engine) as session, session.begin():
            session.add(
                AnalysisRun(
                    id=second_run_id,
                    conversation_id=conversation_id,
                    owner_user_id=other_owner_id,
                    message_id=message_id,
                    expected_idea_version=0,
                    status="completed",
                    stage="done",
                    outcome="analysis",
                    query="query",
                    coverage_json={},
                    config_versions_json={},
                    event_seq_high_water=0,
                    idempotency_key="request-3",
                    request_hash="d" * 64,
                )
            )

        with pytest.raises(IntegrityError), Session(engine) as session, session.begin():
            session.add(
                RunEvidence(
                    run_id=uuid4(),
                    evidence_id=uuid4(),
                    document_id=document_one,
                    revision_id=revision_one,
                    chunk_id=chunk_one,
                    span_start=0,
                    span_end=8,
                    quoted_span="evidence",
                    source_url="https://example.test/one",
                )
            )

        with pytest.raises(IntegrityError), Session(engine) as session, session.begin():
            session.add(
                RunEvidence(
                    run_id=run_id,
                    evidence_id=uuid4(),
                    document_id=document_two,
                    revision_id=revision_two,
                    chunk_id=chunk_one,
                    span_start=0,
                    span_end=8,
                    quoted_span="evidence",
                    source_url="https://example.test/two",
                )
            )

        command.downgrade(config, "base")
        with engine.connect() as connection:
            remaining = (
                connection.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname = current_schema()")
                )
                .scalars()
                .all()
            )
        assert set(remaining) <= {"alembic_version"}
        command.upgrade(config, "head")
    finally:
        engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        admin_engine.dispose()


def test_publication_migration_preserves_legacy_completed_run() -> None:
    assert TEST_DATABASE_URL is not None
    admin_engine = create_engine(TEST_DATABASE_URL)
    schema = f"legacy_run_test_{uuid4().hex}"
    with admin_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped_url = (
        TEST_DATABASE_URL
        + ("&" if "?" in TEST_DATABASE_URL else "?")
        + f"options=-csearch_path%3D{schema}"
    )
    engine = create_engine(scoped_url)
    config = _alembic_config(scoped_url)
    owner_id, conversation_id, message_id, run_id = (uuid4() for _ in range(4))
    try:
        command.upgrade(config, "0003_graph_fact_recovery")
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO users (id, email_normalized) VALUES (:id, :email)"),
                {"id": owner_id, "email": f"{owner_id}@legacy.test"},
            )
            connection.execute(
                text("INSERT INTO conversations (id, owner_user_id) VALUES (:id, :owner)"),
                {"id": conversation_id, "owner": owner_id},
            )
            connection.execute(
                text(
                    "INSERT INTO messages (id, conversation_id, role, content) "
                    "VALUES (:id, :conversation, 'assistant', 'legacy answer')"
                ),
                {"id": message_id, "conversation": conversation_id},
            )
            connection.execute(
                text(
                    "INSERT INTO analysis_runs (id, conversation_id, owner_user_id, message_id, "
                    "expected_idea_version, status, stage, outcome, query, answer_json, "
                    "coverage_json, event_seq_high_water, config_versions_json, idempotency_key, "
                    "request_hash) VALUES (:id, :conversation, :owner, :message, 0, "
                    "'completed', 'completed', 'no_evidence', 'legacy query', '{}'::jsonb, "
                    "'{}'::jsonb, 0, '{}'::jsonb, 'legacy-key', :request_hash)"
                ),
                {
                    "id": run_id,
                    "conversation": conversation_id,
                    "owner": owner_id,
                    "message": message_id,
                    "request_hash": "a" * 64,
                },
            )
        command.upgrade(config, "head")
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT answer_json, analysis_json, public_analysis_json, "
                    "answer_presentation_json, legacy_projection, progress_json "
                    "FROM analysis_runs WHERE id = :id"
                ),
                {"id": run_id},
            ).one()
            assert row.answer_json == {}
            assert row.analysis_json is None
            assert row.public_analysis_json is None
            assert row.answer_presentation_json is None
            assert row.legacy_projection is True
            assert row.progress_json == {}
        command.downgrade(config, "0003_graph_fact_recovery")
        with engine.connect() as connection:
            columns = set(
                connection.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema = current_schema() AND table_name = 'analysis_runs'"
                    )
                ).scalars()
            )
        assert "analysis_json" not in columns
        command.upgrade(config, "head")
    finally:
        engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        admin_engine.dispose()
