import json
from datetime import UTC, datetime, timedelta
from fnmatch import fnmatch
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.integrations.redis_cache import RedisCache
from app.services.conversations import ConversationService
from app.services.memory import MemoryService
from app.services.memory_cache import ScopedStageCache


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.ttls = {}

    def get(self, name):
        return self.values.get(name)

    def set(self, name, value, *, ex):
        self.values[name] = value
        self.ttls[name] = ex

    def incr(self, name):
        value = int(self.values.get(name, 0)) + 1
        self.values[name] = str(value)
        return value

    def expire(self, name, time):
        self.ttls[name] = time

    def eval(self, script, numkeys, epoch_key, key, epoch, payload, ttl):
        if self.values.get(epoch_key, "0") == epoch:
            self.set(key, payload, ex=ttl)

    def delete(self, *names):
        for name in names:
            self.values.pop(name, None)

    def scan_iter(self, *, match):
        return (key for key in self.values if fnmatch(key, match))


def dimensions():
    return {
        "version": {"generation": "g1", "idea": "v1"},
        "models": {"embedding": "e1"},
        "params": {"limit": 10},
        "inputs": {"query": "sensitive"},
    }


@pytest.mark.parametrize("stage,ttl", [("retrieval", 1800), ("rerank", 86400), ("graph", 600)])
def test_stage_scopes_hit_ttl_corruption_and_outage(stage, ttl):
    backend = FakeRedis()
    cache = ScopedStageCache(RedisCache(backend, scope_secret=b"x" * 32))
    owner, chat = uuid4(), uuid4()
    args = dimensions()
    key = cache.key(stage, owner, chat, **args) + ":0"
    assert "sensitive" not in key
    assert key != cache.key(stage, uuid4(), chat, **args) + ":0"
    assert key != cache.key(stage, owner, uuid4(), **args) + ":0"
    for dimension in args:
        assert key != cache.key(stage, owner, chat, **{**args, dimension: {"changed": True}}) + ":0"
    compute = Mock(return_value={"ids": ["id"]})
    authorize = Mock()

    def validate(value):
        if not isinstance(value, dict) or not isinstance(value.get("ids"), list):
            raise ValueError("invalid cache payload")
        return value

    def call():
        return cache.get_or_compute(
            stage, owner, chat, **args, authorize=authorize, validate=validate, compute=compute
        )

    assert call() == {"ids": ["id"]}
    assert backend.ttls[key] == ttl
    assert call() == {"ids": ["id"]}
    assert compute.call_count == 1
    backend.values[key] = "{bad json"
    assert call() == {"ids": ["id"]}
    backend.values[key] = '"wrong shape"'
    assert call() == {"ids": ["id"]}
    assert compute.call_count == 3
    authorize.side_effect = LookupError("scope revoked")
    with pytest.raises(LookupError):
        call()
    assert compute.call_count == 3
    authorize.side_effect = None
    backend.get = Mock(side_effect=ConnectionError())
    backend.set = Mock(side_effect=ConnectionError())
    assert call() == {"ids": ["id"]}
    assert compute.call_count == 4


def test_revoke_only_one_chat_and_mandatory_authorization():
    backend = FakeRedis()
    cache = ScopedStageCache(RedisCache(backend, scope_secret=b"x" * 32))
    owner, a, b = uuid4(), uuid4(), uuid4()
    keys = [cache.key("graph", owner, chat, **dimensions()) for chat in (a, b)]
    for key in keys:
        cache.cache.set_json(key, [1], layer="graph")
    assert cache.invalidate_conversation(owner, a)
    assert cache.cache.get_json(keys[0]) is None
    assert cache.cache.get_json(keys[1]) == [1]
    access = Mock(side_effect=[None, LookupError("deleted during lookup")])
    with pytest.raises(LookupError):
        cache.get_or_compute(
            "graph",
            owner,
            b,
            **dimensions(),
            authorize=access,
            validate=lambda v: v,
            compute=lambda: [],
        )


def test_monotonic_summary_rejects_foreign_and_older_checkpoint():
    owner, chat, old_id, new_id = uuid4(), uuid4(), uuid4(), uuid4()
    now = datetime.now(UTC)
    old = SimpleNamespace(id=old_id, created_at=now)
    new = SimpleNamespace(id=new_id, created_at=now + timedelta(seconds=1))
    conversation = SimpleNamespace(summary_until_message_id=new_id, summary_json={"legacy": True})
    session = Mock()
    session.scalar.side_effect = [conversation, old, new, conversation, None]
    service = ConversationService(session)
    service.set_summary(owner, chat, {"schema_version": 1}, old_id)
    assert conversation.summary_json == {"legacy": True}
    with pytest.raises(LookupError):
        service.set_summary(owner, chat, {}, uuid4())
    assert session.flush.call_count == 0


def test_context_selection_is_stable_and_excludes_recent_from_relevant():
    owner, chat = uuid4(), uuid4()
    now = datetime.now(UTC)
    older = SimpleNamespace(id=uuid4(), content="sensor optical", created_at=now)
    middle = SimpleNamespace(id=uuid4(), content="optical", created_at=now)
    recent = SimpleNamespace(id=uuid4(), content="optical", created_at=now)
    session = Mock()
    session.scalars.return_value = [recent, middle, older]
    service = MemoryService(session)
    service.conversations = Mock()
    service.conversations.current_idea.return_value = None
    service.conversations.summary.return_value = ({"legacy": True}, older.id)
    result = service.context(owner, chat, query="sensor optical", recent_limit=1, relevant_limit=2)
    assert result.recent == (recent,)
    assert result.relevant == (older, middle)
    assert result.summary == {"legacy": True}
    service.conversations.get.assert_called_with(owner, chat)


def test_historical_snapshot_is_pinned_copied_and_owner_scoped():
    owner, chat, source, version_id, generation = (uuid4() for _ in range(5))
    source_run = SimpleNamespace(
        conversation_id=chat,
        status="completed",
        evidence_snapshot_json={"sources": [{"revision": "old"}]},
        idea_version_id=version_id,
        index_generation_id=generation,
    )
    session = Mock()
    version = SimpleNamespace(id=version_id)
    session.scalar.return_value = version
    service = MemoryService(session)
    service.conversations = Mock()
    service.conversations.repository.get_run.return_value = source_run
    service.conversations.repository.evidence.return_value = ["old evidence"]
    result = service.historical(owner, chat, source)
    assert result.idea_version is version
    assert result.generation_id == generation
    assert result.evidence == ("old evidence",)
    result.snapshot["sources"][0]["revision"] = "changed"
    assert source_run.evidence_snapshot_json["sources"][0]["revision"] == "old"
    service.conversations.repository.get_run.assert_called_with(source, owner_id=owner)
    service.conversations.repository.evidence.assert_called_with(source, owner_id=owner)
    for invalid in (
        None,
        SimpleNamespace(conversation_id=uuid4(), status="completed", evidence_snapshot_json={}),
        SimpleNamespace(conversation_id=chat, status="running", evidence_snapshot_json={}),
    ):
        service.conversations.repository.get_run.return_value = invalid
        with pytest.raises(LookupError):
            service.historical(owner, chat, source)


def test_rebuild_summary_uses_versioned_bounded_history():
    owner, chat, last = uuid4(), uuid4(), uuid4()
    checkpoint = SimpleNamespace(id=last, created_at=datetime.now(UTC))
    history = [
        SimpleNamespace(id=uuid4(), role="user", content="x" * 300),
        SimpleNamespace(id=last, role="assistant", content="answer"),
    ]
    session = Mock()
    session.scalar.return_value = checkpoint
    session.scalars.return_value = list(reversed(history))
    service = MemoryService(session)
    service.conversations = Mock()
    service.rebuild_summary(owner, chat, until_message_id=last)
    owner_arg, chat_arg, summary, checkpoint_arg = service.conversations.set_summary.call_args.args
    assert (owner_arg, chat_arg, checkpoint_arg) == (owner, chat, last)
    assert summary["schema_version"] == 1
    assert summary["builder_version"] == "extractive-v1"
    assert [item["id"] for item in summary["messages"]] == [str(m.id) for m in history]
    assert len(summary["messages"][0]["excerpt"]) == 256


def test_empty_context():
    session = Mock()
    session.scalars.return_value = []
    service = MemoryService(session)
    service.conversations = Mock()
    service.conversations.current_idea.return_value = None
    service.conversations.summary.return_value = (None, None)
    context = service.context(uuid4(), uuid4(), query="unseen")
    assert (context.recent, context.relevant, context.summary, context.idea_version) == (
        (),
        (),
        None,
        None,
    )


def test_late_write_is_fenced_even_after_authorization():
    backend = FakeRedis()
    cache = ScopedStageCache(RedisCache(backend, scope_secret=b"x" * 32))
    owner, chat = uuid4(), uuid4()

    def compute():
        assert cache.invalidate_conversation(owner, chat)
        return {"ids": ["late"]}

    result = cache.get_or_compute(
        "retrieval",
        owner,
        chat,
        **dimensions(),
        authorize=lambda: None,
        validate=lambda value: value,
        compute=compute,
    )
    assert result == {"ids": ["late"]}
    assert not any(key.startswith("stage:v3:") for key in backend.values)


def test_worker_rerank_cache_uses_scope_inputs_and_authorizes():
    import asyncio
    from unittest.mock import AsyncMock

    from app.domain.evidence import CandidateEvidence
    from app.services.analysis_run import AnalysisRunService

    backend = FakeRedis()
    service = AnalysisRunService.__new__(AnalysisRunService)
    service.stage_cache = ScopedStageCache(RedisCache(backend, scope_secret=b"x" * 32))
    service.retrieval_config_hash = "a" * 64
    service.session_factory = Mock()
    service.rerank = AsyncMock(return_value=[0.5])
    service._authorize_cache = Mock()
    from contextlib import nullcontext
    from unittest.mock import patch

    data = SimpleNamespace(
        owner_id=uuid4(), conversation_id=uuid4(), query="private canary", request_id="request"
    )
    item = CandidateEvidence(
        uuid4(),
        uuid4(),
        uuid4(),
        "openalex",
        "x",
        "url",
        "title",
        "paper",
        None,
        "section",
        "en",
        "text",
        ("metadata",),
        1.0,
    )

    generation = uuid4()

    async def exercise():
        for _ in range(2):
            assert await service._cached_rerank(
                data, (item,), generation, "worker", 1, 5, asyncio.Event()
            ) == [0.5]
        assert service.rerank.await_count == 1
        data.query = "other"
        await service._cached_rerank(data, (item,), generation, "worker", 1, 5, asyncio.Event())
        assert service.rerank.await_count == 2
        from dataclasses import replace

        await service._cached_rerank(
            data, (replace(item, title="other"),), generation, "worker", 1, 5, asyncio.Event()
        )
        await service._cached_rerank(
            data, (replace(item, section="other"),), generation, "worker", 1, 5, asyncio.Event()
        )
        await service._cached_rerank(data, (item,), uuid4(), "worker", 1, 5, asyncio.Event())
        assert service.rerank.await_count == 5

    with patch("app.services.analysis_run.conversation_write_guard", return_value=nullcontext()):
        asyncio.run(exercise())
    assert service._authorize_cache.call_count >= 4
    assert all(
        "private canary" not in str(key) and "private canary" not in str(value)
        for key, value in backend.values.items()
    )


def test_cache_telemetry_contains_only_stage_and_outcome(caplog, monkeypatch):
    import logging

    backend = FakeRedis()
    cache = ScopedStageCache(RedisCache(backend, scope_secret=b"x" * 32))
    owner, chat = uuid4(), uuid4()
    monkeypatch.setattr(logging.getLogger("app.services.memory_cache"), "disabled", False)
    caplog.set_level(logging.INFO, logger="app.services.memory_cache")

    def invoke():
        return cache.get_or_compute(
            "graph",
            owner,
            chat,
            **dimensions(),
            authorize=lambda: None,
            validate=lambda value: value,
            compute=lambda: {"secret": "canary"},
        )

    invoke()
    invoke()
    backend.get = Mock(side_effect=ConnectionError())
    invoke()
    assert [r.message for r in caplog.records] == [
        "stage_cache stage=graph outcome=miss",
        "stage_cache stage=graph outcome=hit",
        "stage_cache stage=graph outcome=unavailable",
    ]
    assert all(
        "canary" not in r.message and str(owner) not in r.message and str(chat) not in r.message
        for r in caplog.records
    )


def test_worker_retrieval_hit_rechecks_membership_and_generation():
    import asyncio
    from contextlib import nullcontext
    from unittest.mock import AsyncMock, patch

    from app.domain.contracts import CoverageV1
    from app.domain.evidence import CandidateEvidence, RetrievalResult
    from app.domain.planner import IdeaV1
    from app.services.analysis_run import AnalysisRunService
    from app.services.retrieval import build_retrieval_query

    backend = FakeRedis()
    service = AnalysisRunService.__new__(AnalysisRunService)
    service.stage_cache = ScopedStageCache(RedisCache(backend, scope_secret=b"x" * 32))
    service.retrieval_config_hash = "a" * 64
    service.session_factory = Mock()
    service._authorize_cache = Mock()
    service.retrieval = Mock()
    service.retrieval.config.max_features = 8
    data = SimpleNamespace(
        owner_id=uuid4(), conversation_id=uuid4(), query="canary", request_id="request"
    )
    idea = IdeaV1(features=[])
    generation = uuid4()
    item = CandidateEvidence(
        uuid4(),
        uuid4(),
        uuid4(),
        "openalex",
        "x",
        "url",
        "title",
        "paper",
        None,
        "section",
        "en",
        "text",
        ("metadata",),
        1.0,
    )
    coverage = CoverageV1(sources=[], channels=[], partial=False, historical=False)
    service.retrieval.search = AsyncMock(
        return_value=RetrievalResult(
            generation, build_retrieval_query(data.query, idea), (item,), coverage
        )
    )
    service.retrieval._load_candidates_by_chunk_ids.return_value = (item,)

    async def exercise():
        first = await service._cached_retrieval(data, idea, generation, "worker", 1)
        second = await service._cached_retrieval(data, idea, generation, "worker", 1)
        assert first == second
        assert service.retrieval.search.await_count == 1
        assert service.retrieval._load_candidates_by_chunk_ids.call_count >= 3
        await service._cached_retrieval(data, idea, uuid4(), "worker", 1)
        assert service.retrieval.search.await_count == 2

    with patch("app.services.analysis_run.conversation_write_guard", return_value=nullcontext()):
        asyncio.run(exercise())
    assert all(
        "canary" not in str(key) and "canary" not in str(value)
        for key, value in backend.values.items()
    )


def test_read_persisted_idea_accepts_uuid_from_jsonb():
    from app.domain.planner import IdeaV1
    from app.services.analysis_run import AnalysisRunService

    idea = IdeaV1.model_validate_json(
        json.dumps({"features": [{"id": str(uuid4()), "text": "fixture", "weight": 1.0}]})
    )
    version = SimpleNamespace(normalized_json=idea.model_dump(mode="json"))
    assert AnalysisRunService._idea(version) == idea


@pytest.mark.parametrize("error", ["worker", "graph"])
def test_removed_conversation_guard_returns_scoped_error(error):
    from contextlib import nullcontext

    from fastapi import HTTPException

    from app.services.analysis_run import LeaseLost
    from app.services.memory_cache import conversation_write_guard

    db = Mock()
    db.scalar.return_value = None
    sessions = Mock()
    sessions.begin.return_value = nullcontext(db)
    expected = (
        LeaseLost("conversation lost") if error == "worker" else HTTPException(404, "NOT_FOUND")
    )
    with pytest.raises(type(expected)) as raised:
        with conversation_write_guard(sessions, uuid4(), uuid4(), missing_error=lambda: expected):
            pytest.fail("guard accepted a deleted conversation")
    assert raised.value is expected


def test_worker_cache_write_deletion_is_lease_lost():
    import asyncio
    from contextlib import contextmanager
    from unittest.mock import AsyncMock, patch

    from app.domain.evidence import CandidateEvidence
    from app.services.analysis_run import AnalysisRunService, LeaseLost

    @contextmanager
    def missing(*args, missing_error):
        raise missing_error()
        yield

    service = AnalysisRunService.__new__(AnalysisRunService)
    service.stage_cache = ScopedStageCache(RedisCache(FakeRedis(), scope_secret=b"x" * 32))
    service.session_factory = Mock()
    service.retrieval_config_hash = "a" * 64
    service.rerank = AsyncMock(return_value=[0.5])
    service._authorize_cache = Mock()
    data = SimpleNamespace(
        owner_id=uuid4(), conversation_id=uuid4(), query="fixture", request_id="r"
    )
    item = CandidateEvidence(
        uuid4(),
        uuid4(),
        uuid4(),
        "openalex",
        "x",
        "url",
        "title",
        "paper",
        None,
        "section",
        "en",
        "text",
        ("metadata",),
        1.0,
    )
    with patch("app.services.analysis_run.conversation_write_guard", missing):
        with pytest.raises(LeaseLost):
            asyncio.run(
                service._cached_rerank(data, (item,), uuid4(), "worker", 1, 5, asyncio.Event())
            )


def test_graph_cache_write_deletion_is_404():
    from contextlib import contextmanager
    from unittest.mock import patch

    from fastapi import HTTPException

    from app.api.routes.graph import graph

    @contextmanager
    def missing(*args, missing_error):
        raise missing_error()
        yield

    cache = ScopedStageCache(RedisCache(FakeRedis(), scope_secret=b"x" * 32))
    owner = SimpleNamespace(user_id=uuid4())
    run = SimpleNamespace(
        id=uuid4(),
        conversation_id=uuid4(),
        idea_version_id=None,
        config_versions_json={},
        evidence_snapshot_json={},
        answer_json={},
    )
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(stage_cache=cache)))
    db = Mock()
    db.get_bind.return_value = None
    with (
        patch("app.api.routes.graph._run", return_value=run),
        patch("app.api.routes.graph._snapshot", return_value={}),
        patch("app.api.routes.graph.conversation_write_guard", missing),
    ):
        with pytest.raises(HTTPException) as raised:
            graph(run.id, owner, db, request)
    assert raised.value.status_code == 404
