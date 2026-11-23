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
    key = cache.key(stage, owner, chat, **args)
    assert "sensitive" not in key
    assert key != cache.key(stage, uuid4(), chat, **args)
    assert key != cache.key(stage, owner, uuid4(), **args)
    for dimension in args:
        assert key != cache.key(stage, owner, chat, **{**args, dimension: {"changed": True}})
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
