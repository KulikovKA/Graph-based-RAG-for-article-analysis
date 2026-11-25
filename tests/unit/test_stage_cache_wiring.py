"""Проверка настройки общего и совместимого кэша без подключения к Redis."""

import hashlib
from uuid import uuid4

import pytest
from redis import Redis

from app.main import _stage_cache, create_app
from app.services.memory_cache import build_stage_cache


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    class Client:
        pass

    monkeypatch.setattr(Redis, "from_url", lambda *args, **kwargs: Client())
    for name in ("REDIS_URL", "STAGE_CACHE_SCOPE_SECRET", "AUTH_SESSION_SECRET"):
        monkeypatch.delenv(name, raising=False)


def test_new_scope_secret_matches_worker(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://synthetic.invalid/0")
    monkeypatch.setenv("STAGE_CACHE_SCOPE_SECRET", "synthetic-shared")
    monkeypatch.setenv("AUTH_SESSION_SECRET", "synthetic-auth")
    api_cache = create_app().state.stage_cache
    worker_cache = build_stage_cache("redis://synthetic.invalid/0", "synthetic-shared")
    assert api_cache is not None and worker_cache is not None
    owner, chat = uuid4(), uuid4()
    kwargs = dict(version="v", models="m", params={}, inputs={})
    assert api_cache.key("graph", owner, chat, **kwargs) == worker_cache.key(
        "graph", owner, chat, **kwargs
    )
    assert api_cache.cache.scope_secret != hashlib.sha256(
        b"article-stage-cache-v1\x00" + b"synthetic-auth"
    ).digest()


def test_legacy_fallback_keeps_exact_key(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://synthetic.invalid/0")
    monkeypatch.setenv("AUTH_SESSION_SECRET", "synthetic-auth")
    cache = _stage_cache()
    assert cache is not None
    assert cache.cache.scope_secret == hashlib.sha256(
        b"article-stage-cache-v1\x00" + b"synthetic-auth"
    ).digest()


def test_missing_configuration_disables_cache(monkeypatch):
    assert _stage_cache() is None
    monkeypatch.setenv("STAGE_CACHE_SCOPE_SECRET", "synthetic-shared")
    monkeypatch.setenv("AUTH_SESSION_SECRET", "synthetic-auth")
    assert _stage_cache() is None
    monkeypatch.delenv("AUTH_SESSION_SECRET")
    monkeypatch.setenv("REDIS_URL", "redis://synthetic.invalid/0")
    monkeypatch.delenv("STAGE_CACHE_SCOPE_SECRET")
    assert _stage_cache() is None


def test_explicit_cache_injection_takes_precedence(monkeypatch):
    injected = object()
    monkeypatch.setattr("app.main._stage_cache", lambda: pytest.fail("unexpected cache creation"))
    app = create_app(stage_cache=injected)
    assert app.state.stage_cache is injected
