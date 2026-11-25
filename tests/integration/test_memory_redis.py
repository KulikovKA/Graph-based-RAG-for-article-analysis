"""Проверка Redis и PostgreSQL; требуются изолированные TEST_*_URL."""

import os
import socket
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session, sessionmaker
from tests.integration import test_repositories

from app.integrations.redis_cache import RedisCache
from app.services.conversations import ConversationService
from app.services.memory_cache import ScopedStageCache, conversation_write_guard
from app.storage.models import User

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL") or not os.getenv("TEST_REDIS_URL"),
    reason="изолированные PostgreSQL и Redis не настроены",
)
engine = test_repositories.engine


@pytest.fixture
def redis_client():
    # При заданном URL отсутствие драйвера считается ошибкой среды, а не пропуском теста.
    from redis import Redis

    client = Redis.from_url(
        os.environ["TEST_REDIS_URL"], socket_connect_timeout=1, socket_timeout=1
    )
    client.ping()
    yield client
    client.close()


@pytest.mark.parametrize("stage,ttl", [("retrieval", 1800), ("rerank", 86400), ("graph", 600)])
def test_live_cache_hit_isolation_invalidation_and_revocation(engine, redis_client, stage, ttl):
    owner, stranger = uuid4(), uuid4()
    secret = uuid4().bytes + uuid4().bytes
    cache = ScopedStageCache(RedisCache(redis_client, scope_secret=secret))
    dimensions = {"version": {"generation": "v1"}, "models": {}, "params": {}, "inputs": {}}
    with Session(engine) as session, session.begin():
        session.add_all(
            User(id=user, email_normalized=f"{user}@example.test") for user in (owner, stranger)
        )
        session.flush()
        service = ConversationService(session)
        chat = service.create(owner).id
        other_chat = service.create(owner).id
        stranger_chat = service.create(stranger).id

    calls = []

    def invoke(user, conversation, version="v1"):
        def authorize():
            # Новая транзакция не позволяет старой сессии скрыть удаление чата.
            with Session(engine) as session:
                ConversationService(session).get(user, conversation)

        def compute():
            calls.append((user, conversation, version))
            return {"ids": [str(uuid4())]}

        return cache.get_or_compute(
            stage,
            user,
            conversation,
            **{**dimensions, "version": {"generation": version}},
            authorize=authorize,
            validate=lambda value: value,
            compute=compute,
        )

    try:
        first = invoke(owner, chat)
        key = cache.key(stage, owner, chat, **dimensions) + ":0"
        assert 0 < redis_client.ttl(key) <= ttl
        assert invoke(owner, chat) == first
        assert len(calls) == 1
        assert invoke(owner, chat, "v2") != first
        assert invoke(owner, other_chat) != first
        assert invoke(stranger, stranger_chat) != first
        assert len(calls) == 4
        with pytest.raises(LookupError):
            invoke(stranger, chat)
        assert len(calls) == 4
        assert cache.invalidate_conversation(owner, chat)
        assert redis_client.get(key) is None
        assert invoke(owner, chat) != first
        assert len(calls) == 5
        with Session(engine) as session, session.begin():
            ConversationService(session).delete(owner, chat)
        # Даже если физическая очистка задерживается, SQL запрещает cache hit.
        assert redis_client.get(cache.key(stage, owner, chat, **dimensions) + ":1") is not None
        with pytest.raises(LookupError):
            invoke(owner, chat)
        assert len(calls) == 5
        assert cache.invalidate_conversation(owner, chat)
        assert redis_client.get(key) is None
        assert invoke(owner, other_chat)
        assert len(calls) == 5
    finally:
        for user, conversation in ((owner, chat), (owner, other_chat), (stranger, stranger_chat)):
            assert cache.invalidate_conversation(user, conversation)


def test_real_connection_failure_degrades_to_miss(engine):
    from redis import Redis

    owner = uuid4()
    with Session(engine) as session, session.begin():
        session.add(User(id=owner, email_normalized=f"{owner}@example.test"))
        session.flush()
        chat = ConversationService(session).create(owner).id
    # Зарезервированный сокет не слушает: соединение Redis гарантированно отклоняется.
    with socket.socket() as unavailable:
        unavailable.bind(("127.0.0.1", 0))
        port = unavailable.getsockname()[1]
        client = Redis(host="127.0.0.1", port=port, socket_connect_timeout=1, socket_timeout=1)
        try:
            cache = ScopedStageCache(RedisCache(client, scope_secret=b"x" * 32))

            def authorize():
                with Session(engine) as session:
                    ConversationService(session).get(owner, chat)

            result = cache.get_or_compute(
                "retrieval",
                owner,
                chat,
                version={},
                models={},
                params={},
                inputs={},
                authorize=authorize,
                validate=lambda value: value,
                compute=lambda: {"ids": ["fallback"]},
            )
            assert result == {"ids": ["fallback"]}
            assert not cache.invalidate_conversation(owner, chat)
        finally:
            client.close()


def test_live_late_write_is_atomic_after_revocation(engine, redis_client):
    owner = uuid4()
    with Session(engine) as session, session.begin():
        session.add(User(id=owner, email_normalized=f"{owner}@example.test"))
        session.flush()
        chat = ConversationService(session).create(owner).id
    cache = ScopedStageCache(RedisCache(redis_client, scope_secret=uuid4().bytes + uuid4().bytes))
    dimensions = {"version": {}, "models": {}, "params": {}, "inputs": {}}

    checks = 0

    def authorize():
        nonlocal checks
        with Session(engine) as session:
            ConversationService(session).get(owner, chat)
        checks += 1
        if checks == 2:
            # ???????? ?????????? ??????????????? ????? ???????? ????? SET.
            with Session(engine) as session, session.begin():
                ConversationService(session).delete(owner, chat)
            assert cache.invalidate_conversation(owner, chat)

    def compute():
        return {"ids": ["late"]}

    assert cache.get_or_compute(
        "retrieval",
        owner,
        chat,
        **dimensions,
        authorize=authorize,
        validate=lambda value: value,
        compute=compute,
    ) == {"ids": ["late"]}
    assert redis_client.get(cache.key("retrieval", owner, chat, **dimensions) + ":0") is None
    redis_client.delete(cache._epoch_key(owner, chat))


def test_late_write_after_redis_epoch_loss_is_blocked_by_database(engine, redis_client):
    owner = uuid4()
    with Session(engine) as session, session.begin():
        session.add(User(id=owner, email_normalized=f"{owner}@example.test"))
        session.flush()
        chat = ConversationService(session).create(owner).id
    cache = ScopedStageCache(RedisCache(redis_client, scope_secret=uuid4().bytes + uuid4().bytes))
    dims = {"version": {}, "models": {}, "params": {}, "inputs": {}}
    checks = 0

    def authorize():
        nonlocal checks
        with Session(engine) as session:
            ConversationService(session).get(owner, chat)
        checks += 1
        if checks == 2:
            with Session(engine) as session, session.begin():
                ConversationService(session).delete(owner, chat)
            assert cache.invalidate_conversation(owner, chat)
            redis_client.delete(cache._epoch_key(owner, chat))

    with pytest.raises(LookupError):
        cache.get_or_compute(
            "retrieval",
            owner,
            chat,
            **dims,
            authorize=authorize,
            validate=lambda value: value,
            compute=lambda: {"ids": ["late"]},
            write_guard=lambda: conversation_write_guard(sessionmaker(bind=engine), owner, chat),
        )
    assert redis_client.get(cache.key("retrieval", owner, chat, **dims) + ":0") is None
