"""Контракты истории и жизненного цикла чата на PostgreSQL."""

import asyncio
import os
from datetime import timedelta
from typing import cast
from uuid import UUID

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from tests.contract.test_api import accepted, complete

from app.api.routes.conversations import RenameInput
from app.integrations.redis_cache import RedisCache
from app.services.analysis_run import AnalysisRunService
from app.services.memory_cache import ScopedStageCache
from app.storage.jobs import JobRepository
from app.storage.models import AnalysisJob, AnalysisRun, Conversation, Message, SourceDocument
from app.workers.analysis import AnalysisWorker, AnalysisWorkerConfig

pytest_plugins = ("tests.contract.test_api",)


@pytest.mark.parametrize(
    "body", [{}, {"title": " "}, {"title": "x" * 161}, {"title": 1}, {"title": "x", "extra": 1}]
)
def test_rename_contract_rejects_invalid_input(body) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValidationError):
        RenameInput.model_validate(body)


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="no PostgreSQL test DB")
def test_history_rename_and_isolation(api) -> None:  # type: ignore[no-untyped-def]
    service, _, alice, bob = api
    chat, first = accepted(alice)
    empty = alice.post("/api/v1/conversations", json={}).json()["id"]
    assert alice.get(f"/api/v1/conversations/{empty}/runs").json() == {
        "items": [],
        "next_cursor": None,
    }
    complete(service, first)
    second_response = alice.post(
        f"/api/v1/conversations/{chat}/messages",
        headers={"Idempotency-Key": "second"},
        json={"content": "Другая идея", "expected_idea_version": 0, "analyze": True},
    )
    assert second_response.status_code == 202, second_response.text
    second = second_response.json()["run_id"]
    with service.sessions.begin() as db:
        original = db.get(AnalysisRun, UUID(first))
        newer = db.get(AnalysisRun, UUID(second))
        assert original is not None and newer is not None
        newer.created_at = original.created_at
    other, _ = accepted(alice)
    path = f"/api/v1/conversations/{chat}"
    assert alice.patch(path, json={"title": "Новое имя"}).json()["title"] == "Новое имя"
    for invalid in ({}, {"title": " "}, {"title": "x" * 161}, {"title": "x", "bad": 1}):
        assert alice.patch(path, json=invalid).status_code == 422
    assert bob.patch(path, json={"title": "Чужое"}).status_code == 404
    assert bob.delete(path).status_code == 404
    assert bob.get(path + "/runs").status_code == 404
    first_page = alice.get(path + "/runs", params={"limit": 1}).json()
    expected = sorted((first, second), reverse=True)
    assert first_page["items"][0]["id"] == expected[0]
    assert set(first_page["items"][0]) == {
        "id",
        "status",
        "outcome",
        "created_at",
        "completed_at",
        "idea_version_id",
        "index_generation_id",
    }
    cursor = first_page["next_cursor"]
    page2 = alice.get(path + "/runs", params={"limit": 1, "cursor": cursor}).json()
    assert page2["items"][0]["id"] == expected[1]
    assert {first_page["items"][0]["status"], page2["items"][0]["status"]} == {
        "pending",
        "completed",
    }
    assert page2["next_cursor"] is None
    assert (
        alice.get(f"/api/v1/conversations/{other}/runs", params={"cursor": cursor}).status_code
        == 400
    )
    assert alice.get(path + "/runs", params={"cursor": "invalid"}).status_code == 400
    assert alice.patch(path, json={"title": None}).json()["title"] is None
    alice.cookies.clear()
    assert alice.patch(path, json={"title": "Нельзя"}).status_code == 401
    assert alice.delete(path).status_code == 401
    login = alice.post(
        "/api/v1/auth/login",
        headers={"Origin": "https://api.example.test"},
        json={"email": "alice@example.test", "password": "synthetic-api-password"},
    )
    assert login.status_code == 200
    alice.headers["X-CSRF-Token"] = login.json()["csrf_token"]
    csrf = alice.headers.pop("X-CSRF-Token")
    assert alice.patch(path, json={"title": "Нельзя"}).status_code == 403
    assert alice.delete(path).status_code == 403
    alice.headers["X-CSRF-Token"] = csrf


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="no PostgreSQL test DB")
def test_delete_fences_worker_and_invalidates_after_commit(api) -> None:  # type: ignore[no-untyped-def]
    service, app, alice, _ = api
    chat, run = accepted(alice)
    run_id, chat_id = UUID(run), UUID(chat)
    with service.sessions.begin() as db:
        lease = JobRepository(db).claim(run_id, worker="worker", duration=timedelta(minutes=1))
        assert lease is not None
        source = SourceDocument(
            source="test",
            external_id="public",
            canonical_url="https://example.test",
            kind="article",
            title="Источник",
        )
        db.add(source)
        db.flush()
        source_id = source.id

    class Cache:
        called = False

        def invalidate_conversation(self, owner_id, conversation_id):  # type: ignore[no-untyped-def]
            with service.sessions() as db:
                assert db.get(Conversation, conversation_id) is None
            self.called = True
            raise RuntimeError("Redis недоступен")

    cache = Cache()
    app.state.stage_cache = cache
    assert alice.delete(f"/api/v1/conversations/{chat}").status_code == 204
    assert cache.called
    assert alice.get(f"/api/v1/conversations/{chat}").status_code == 404
    assert alice.get(f"/api/v1/runs/{run}").status_code == 404
    with service.sessions.begin() as db:
        assert db.get(Conversation, chat_id) is None
        assert db.get(AnalysisRun, run_id) is None
        assert db.get(AnalysisJob, run_id) is None
        assert db.scalar(select(Message).where(Message.conversation_id == chat_id)) is None
        assert db.get(SourceDocument, source_id) is not None
        assert not JobRepository(db).heartbeat(
            run_id, worker="worker", token=lease, duration=timedelta(minutes=1)
        )
        assert not JobRepository(db).complete(
            run_id, worker="worker", token=lease, outcome="no_evidence", answer={}, coverage={}
        )


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="no PostgreSQL test DB")
def test_delete_cancels_heartbeat_of_active_worker(api) -> None:  # type: ignore[no-untyped-def]
    service, _, alice, _ = api
    chat, run = accepted(alice)

    class WaitingAnalysis:
        started: asyncio.Event
        stopped: asyncio.Event

        async def execute(self, _run_id, *, cancel, **_kwargs):  # type: ignore[no-untyped-def]
            self.started.set()
            await cancel.wait()
            self.stopped.set()
            return object()

    async def exercise() -> None:
        analysis = WaitingAnalysis()
        analysis.started = asyncio.Event()
        analysis.stopped = asyncio.Event()
        worker = AnalysisWorker(
            service.sessions,
            cast(AnalysisRunService, analysis),
            config=AnalysisWorkerConfig(
                worker_id="chat-deletion", lease_seconds=10, heartbeat_seconds=0.05
            ),
        )
        task = asyncio.create_task(worker.run_once())
        try:
            await asyncio.wait_for(analysis.started.wait(), timeout=3)
            response = await asyncio.to_thread(alice.delete, f"/api/v1/conversations/{chat}")
            assert response.status_code == 204
            assert await asyncio.wait_for(task, timeout=3)
            assert analysis.stopped.is_set()
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    asyncio.run(exercise())
    assert alice.get(f"/api/v1/runs/{run}").status_code == 404


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="no PostgreSQL test DB")
@pytest.mark.parametrize("locked_row", ["job", "conversation"])
def test_delete_lock_conflict_rolls_back_and_can_retry(api, locked_row) -> None:  # type: ignore[no-untyped-def]
    service, _, alice, _ = api
    chat, run = accepted(alice)
    with service.sessions.begin() as worker:
        statement = (
            select(AnalysisJob).where(AnalysisJob.run_id == UUID(run))
            if locked_row == "job"
            else select(Conversation).where(Conversation.id == UUID(chat))
        )
        worker.scalar(statement.with_for_update())
        response = alice.delete(f"/api/v1/conversations/{chat}")
        assert response.status_code == 503
        assert alice.get(f"/api/v1/conversations/{chat}").status_code == 200
    assert alice.delete(f"/api/v1/conversations/{chat}").status_code == 204


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL") or not os.getenv("TEST_REDIS_URL"),
    reason="no PostgreSQL or Redis test service",
)
def test_delete_invalidates_only_owned_chat_in_redis(api) -> None:  # type: ignore[no-untyped-def]
    import redis

    _, app, alice, _ = api
    chat, _ = accepted(alice)
    other = alice.post("/api/v1/conversations", json={"title": "Другой"}).json()["id"]
    owner_id = UUID(alice.get("/api/v1/auth/session").json()["user_id"])
    client = redis.Redis.from_url(os.environ["TEST_REDIS_URL"])
    cache = ScopedStageCache(RedisCache(client, scope_secret=b"synthetic-test-secret-32-bytes!!"))
    app.state.stage_cache = cache

    def key(conversation_id: str) -> str:
        return cache.key(
            "retrieval",
            owner_id,
            UUID(conversation_id),
            version="v1",
            models="m1",
            params={},
            inputs={},
        )

    target_key, other_key = key(chat), key(other)
    try:
        client.set(target_key, "{}", ex=60)
        client.set(other_key, "{}", ex=60)
        assert alice.delete(f"/api/v1/conversations/{chat}").status_code == 204
        assert client.get(target_key) is None
        assert client.get(other_key) == b"{}"
        assert alice.get(f"/api/v1/conversations/{chat}").status_code == 404
    finally:
        client.delete(target_key, other_key)
        client.close()
