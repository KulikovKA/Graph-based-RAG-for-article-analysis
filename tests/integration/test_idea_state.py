"""Planner/CAS, исторический snapshot и повтор worker на реальном PostgreSQL."""

import json
import os
from datetime import timedelta
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, null, select, text
from sqlalchemy.orm import Session

from app.domain.planner import PlannerV1, PlannerViolation
from app.services.idea_state import IdeaStateService, PlannerFenceLost
from app.storage.jobs import JobRepository
from app.storage.models import (
    AnalysisJob,
    AnalysisRun,
    Conversation,
    DocumentRevision,
    EvidenceChunk,
    Idea,
    IdeaVersion,
    IndexGeneration,
    RunEvidence,
    SourceDocument,
    User,
    utcnow,
)
from app.storage.repositories import OwnedRepository, VersionConflict

pytestmark = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="no PostgreSQL test DB")


@pytest.fixture
def engine():  # type: ignore[no-untyped-def]
    url = os.environ["TEST_DATABASE_URL"]
    admin = create_engine(url)
    schema = f"planner_test_{uuid4().hex}"
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


def plan(version, intent="clarify", **changes):  # type: ignore[no-untyped-def]
    return PlannerV1.model_validate_json(
        json.dumps(
            {
                "schema_version": 1,
                "intent": intent,
                "base_idea_version": version,
                "add_features": [],
                "remove_feature_ids": [],
                "replace_features": [],
                "focus_evidence_ids": [],
                "suggested_retrieval": False,
                "confidence": 0.9,
                **changes,
            }
        )
    )


def accept(session, owner, conversation, version, source=None):  # type: ignore[no-untyped-def]
    run, _ = OwnedRepository(session).accept_run(
        owner_id=owner,
        conversation_id=conversation,
        expected_idea_version=version,
        content="fixture",
        query="fixture",
        idempotency_key=uuid4().hex,
        request_hash="a" * 64,
        source_run_id=source,
    )
    token = JobRepository(session).claim(run.id, worker="planner", duration=timedelta(minutes=5))
    assert token == 1
    return run


def apply(session, owner, run, generation, proposal, **changes):  # type: ignore[no-untyped-def]
    return IdeaStateService(session).apply(
        owner_id=owner,
        run_id=run.id,
        worker="planner",
        lease_token=1,
        plan=proposal,
        generation_id=generation,
        retrieval_config_hash="b" * 64,
        query_hash="c" * 64,
        **changes,
    )


def complete(session, run):  # type: ignore[no-untyped-def]
    assert JobRepository(session).complete(
        run.id,
        worker="planner",
        token=1,
        outcome="analysis",
        answer={},
        coverage={},
    )


@pytest.fixture
def saved(engine):  # type: ignore[no-untyped-def]
    owner, conversation, generation, newer = uuid4(), uuid4(), uuid4(), uuid4()
    with Session(engine) as session, session.begin():
        session.add(User(id=owner, email_normalized=f"{owner}@example.test"))
        session.flush()
        session.add(Conversation(id=conversation, owner_user_id=owner))
        session.add_all(
            [
                IndexGeneration(id=generation, config_versions_json={}),
                IndexGeneration(id=newer, config_versions_json={}),
            ]
        )
        session.flush()
        run = accept(session, owner, conversation, 0)
        applied = apply(
            session,
            owner,
            run,
            generation,
            plan(
                0,
                "new_idea",
                add_features=[
                    {"text": "OCR", "rationale": "запрос"},
                    {"text": "Камера", "rationale": "запрос"},
                ],
            ),
        )
        assert applied.decision.requires_retrieval
        version = applied.idea_version
        assert version is not None
        feature_id = version.normalized_json["features"][0]["id"]
        sources = []
        evidence_ids = []
        for ordinal in (1, 2):
            document = SourceDocument(
                source="fixture",
                external_id=str(ordinal),
                kind="patent",
                title=f"Патент {ordinal}",
                canonical_url=f"https://example.test/{ordinal}",
            )
            session.add(document)
            session.flush()
            revision = DocumentRevision(
                document_id=document.id,
                content_hash=str(ordinal) * 64,
                normalized_json={},
                ingest_state="normalized",
            )
            session.add(revision)
            session.flush()
            chunk = EvidenceChunk(
                revision_id=revision.id,
                section="abstract",
                ordinal=0,
                text="OCR 📷",
                section_start=0,
                section_end=5,
                hash="d" * 64,
                language="en",
            )
            session.add(chunk)
            session.flush()
            evidence = RunEvidence(
                run_id=run.id,
                document_id=document.id,
                revision_id=revision.id,
                chunk_id=chunk.id,
                span_start=0,
                span_end=5,
                quoted_span="OCR 📷",
                source_url=document.canonical_url,
                index_generation_id=generation,
            )
            session.add(evidence)
            session.flush()
            evidence_ids.append(evidence.evidence_id)
            sources.append(
                {
                    "document_id": str(document.id),
                    "title": document.title,
                    "evidence_ids": [str(evidence.evidence_id)],
                }
            )
        run.evidence_snapshot_json = {"sources": sources, "fixture": "immutable"}
        complete(session, run)
        return {
            "owner": owner,
            "conversation": conversation,
            "generation": generation,
            "newer": newer,
            "source": run.id,
            "version": version.id,
            "feature": feature_id,
            "evidence": evidence_ids,
        }


def test_patch_retry_and_historical_second_patent(engine, saved) -> None:  # type: ignore[no-untyped-def]
    s = saved
    with Session(engine) as session, session.begin():
        run = accept(session, s["owner"], s["conversation"], 1)
        proposal = plan(
            1,
            "modify_idea",
            replace_features=[
                {"feature_id": s["feature"], "text": "barcode", "rationale": "запрос"},
            ],
        )
        result = apply(session, s["owner"], run, s["newer"], proposal)
        assert result.idea_version.version_no == 2
        assert result.idea_version.normalized_json["features"][0]["id"] == s["feature"]
        assert result.decision.requires_retrieval
        run_id, current_id = run.id, result.idea_version.id
    # Другая сессия моделирует повтор worker после commit/потери ответа.
    with Session(engine) as session, session.begin():
        run = session.get(AnalysisRun, run_id)
        result = apply(session, s["owner"], run, s["newer"], plan(999))
        assert result.idea_version.id == current_id
        assert session.scalar(select(func.count()).select_from(IdeaVersion)) == 2
        complete(session, run)
    with Session(engine) as session, session.begin():
        run = accept(session, s["owner"], s["conversation"], 2, s["source"])
        context = IdeaStateService(session).context(owner_id=s["owner"], run_id=run.id)
        assert context.sources[1].ordinal == 2
        assert context.sources[1].evidence_ids == [s["evidence"][1]]
        result = apply(
            session,
            s["owner"],
            run,
            s["newer"],
            plan(2, "explain_evidence", focus_evidence_ids=[str(s["evidence"][1])]),
        )
        assert not result.decision.requires_retrieval and result.decision.historical
        assert result.idea_version.id == s["version"]
        assert session.scalar(select(Idea.current_version_id)) == current_id
        source = session.get(AnalysisRun, s["source"])
        assert run.evidence_snapshot_json == source.evidence_snapshot_json
        assert run.index_generation_id == s["generation"]
        assert run.coverage_json["historical"]
        copied = OwnedRepository(session).evidence(run.id, owner_id=s["owner"])
        assert {e.evidence_id for e in copied} == set(s["evidence"])
        assert all(e.quoted_span == "OCR 📷" and e.span_end == 5 for e in copied)
        apply(session, s["owner"], run, s["newer"], plan(2))
        assert len(OwnedRepository(session).evidence(run.id, owner_id=s["owner"])) == 2


def test_clarify_without_idea_is_idempotent(engine) -> None:  # type: ignore[no-untyped-def]
    owner, conversation, generation = uuid4(), uuid4(), uuid4()
    with Session(engine) as session, session.begin():
        session.add(User(id=owner, email_normalized=f"{owner}@example.test"))
        session.flush()
        session.add(Conversation(id=conversation, owner_user_id=owner))
        session.add(IndexGeneration(id=generation, config_versions_json={}))
        session.flush()
        run = accept(session, owner, conversation, 0)
        first = apply(session, owner, run, generation, plan(0))
        second = apply(
            session,
            owner,
            run,
            generation,
            plan(
                0,
                "new_idea",
                add_features=[
                    {"text": "must not be applied", "rationale": "retry"},
                ],
            ),
        )
        assert first.idea_version is second.idea_version is None
        assert second.decision.intent == "clarify" and not second.decision.requires_retrieval
        assert session.scalar(select(func.count()).select_from(IdeaVersion)) == 0
        assert run.planner_applied_at is not None


@pytest.mark.parametrize(
    "fault", ["id", "plan_version", "current_version", "cancel", "lease", "owner"]
)
def test_invalid_patch_or_fence_never_changes_idea(engine, saved, fault) -> None:  # type: ignore[no-untyped-def]
    s = saved
    with Session(engine) as session, session.begin():
        run = accept(session, s["owner"], s["conversation"], 1)
        run_id = run.id
        if fault == "current_version":
            run.expected_idea_version = 0
        if fault == "cancel":
            run.cancel_requested_at = utcnow()
        if fault == "lease":
            session.get(AnalysisJob, run_id).lease_until = utcnow() - timedelta(seconds=1)
    error = {
        "id": PlannerViolation,
        "plan_version": PlannerViolation,
        "current_version": VersionConflict,
        "cancel": PlannerFenceLost,
        "lease": PlannerFenceLost,
        "owner": LookupError,
    }[fault]
    with pytest.raises(error), Session(engine) as session, session.begin():
        run = session.get(AnalysisRun, run_id)
        apply(
            session,
            uuid4() if fault == "owner" else s["owner"],
            run,
            s["generation"],
            plan(
                999 if fault == "plan_version" else 1,
                "modify_idea",
                replace_features=[
                    {
                        "feature_id": str(uuid4()) if fault == "id" else s["feature"],
                        "text": "barcode",
                        "rationale": "запрос",
                    },
                ],
            ),
        )
    with Session(engine) as session:
        assert session.scalar(select(Idea.current_version_id)) == s["version"]
        assert session.scalar(select(func.count()).select_from(IdeaVersion)) == 1
        assert session.get(AnalysisRun, run_id).planner_applied_at is None


@pytest.mark.parametrize("different_generation", [False, True])
def test_general_followup_reuse_requires_matching_key(engine, saved, different_generation) -> None:  # type: ignore[no-untyped-def]
    s = saved
    with Session(engine) as session, session.begin():
        run = accept(session, s["owner"], s["conversation"], 1, s["source"])
        generation = s["newer"] if different_generation else s["generation"]
        result = apply(session, s["owner"], run, generation, plan(1, "general_followup"))
        assert result.decision.requires_retrieval == different_generation
        assert (run.evidence_snapshot_json is None) == different_generation
        assert session.scalar(select(func.count()).select_from(IdeaVersion)) == 1


def test_source_from_other_conversation_or_unfinished_run_is_rejected(engine, saved) -> None:  # type: ignore[no-untyped-def]
    s = saved
    with Session(engine) as session, session.begin():
        other = Conversation(owner_user_id=s["owner"])
        session.add(other)
        session.flush()
        with pytest.raises(LookupError):
            accept(session, s["owner"], other.id, 0, s["source"])
        source = session.get(AnalysisRun, s["source"])
        source.status, source.outcome, source.answer_json = "failed", None, null()
        session.flush()
        with pytest.raises(LookupError):
            accept(session, s["owner"], s["conversation"], 1, s["source"])


def test_prefetched_run_observes_cancellation_from_another_session(engine, saved) -> None:  # type: ignore[no-untyped-def]
    s = saved
    with Session(engine) as session, session.begin():
        run_id = accept(session, s["owner"], s["conversation"], 1).id
    with Session(engine) as stale:
        run = stale.get(AnalysisRun, run_id)
        assert run.cancel_requested_at is None
        with Session(engine) as other, other.begin():
            assert JobRepository(other).request_cancel(run_id, owner_id=s["owner"])
        with pytest.raises(PlannerFenceLost):
            apply(stale, s["owner"], run, s["generation"], plan(1))
        stale.rollback()
    with Session(engine) as session:
        assert session.get(AnalysisRun, run_id).planner_applied_at is None


def test_snapshot_copy_and_marker_rollback_together(engine, saved) -> None:  # type: ignore[no-untyped-def]
    s = saved
    with Session(engine) as session, session.begin():
        run_id = accept(session, s["owner"], s["conversation"], 1, s["source"]).id
    with pytest.raises(RuntimeError, match="crash"), Session(engine) as session, session.begin():
        run = session.get(AnalysisRun, run_id)
        apply(
            session,
            s["owner"],
            run,
            s["generation"],
            plan(1, "explain_evidence", focus_evidence_ids=[str(s["evidence"][1])]),
        )
        raise RuntimeError("crash")
    with Session(engine) as session, session.begin():
        run = session.get(AnalysisRun, run_id)
        assert run.planner_applied_at is None and run.evidence_snapshot_json is None
        assert OwnedRepository(session).evidence(run_id, owner_id=s["owner"]) == []
        result = apply(
            session,
            s["owner"],
            run,
            s["generation"],
            plan(1, "explain_evidence", focus_evidence_ids=[str(s["evidence"][1])]),
        )
        assert result.decision.historical
        assert len(OwnedRepository(session).evidence(run_id, owner_id=s["owner"])) == 2


def test_unchanged_replace_keeps_version(engine, saved) -> None:  # type: ignore[no-untyped-def]
    s = saved
    with Session(engine) as session, session.begin():
        run = accept(session, s["owner"], s["conversation"], 1, s["source"])
        result = apply(
            session,
            s["owner"],
            run,
            s["generation"],
            plan(
                1,
                "modify_idea",
                replace_features=[
                    {"feature_id": s["feature"], "text": "OCR", "rationale": "тот же признак"}
                ],
            ),
        )
        assert result.idea_version.id == s["version"]
        assert not result.decision.requires_retrieval
        assert session.scalar(select(func.count()).select_from(IdeaVersion)) == 1
