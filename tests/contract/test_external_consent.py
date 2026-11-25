"""Контракт согласия и его проверка при синтетическом запросе."""

import asyncio
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from tests.contract.test_api import ORIGIN, accepted
from tests.contract.test_api import api as api_fixture
from tests.contract.test_api import engine as engine_fixture

from app.api.auth import AuthSettings
from app.main import create_app
from app.storage.models import ExternalConsent

api = api_fixture
engine = engine_fixture

pytestmark = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="no PostgreSQL test DB")


def test_consent_durable_and_scoped(api):
    service, app, alice, bob = api
    conversation, run = accepted(alice)
    path = f"/api/v1/runs/{run}/external-consent"
    assert alice.get(path).json() == {"notice_version": "groq_context_v1", "granted": False}
    assert bob.get(path).status_code == 404
    assert alice.get(f"/api/v1/runs/{uuid4()}/external-consent").status_code == 404
    for body in (
        {},
        {"notice_version": 1},
        {"notice_version": "old"},
        {"notice_version": "groq_context_v1", "extra": True},
    ):
        assert alice.post(path, json=body).status_code == 422
    assert (
        alice.post(
            path,
            json={"notice_version": "groq_context_v1"},
            headers={"Origin": "https://evil.test"},
        ).status_code
        == 403
    )
    assert alice.post(path, json={"notice_version": "groq_context_v1"}).json()["granted"]
    _, other_run = accepted(alice)
    assert not alice.get(f"/api/v1/runs/{other_run}/external-consent").json()["granted"]
    assert (
        alice.post(
            path, json={"notice_version": "groq_context_v1"}, headers={"X-CSRF-Token": "invalid"}
        ).status_code
        == 403
    )
    restarted = TestClient(
        create_app(auth=service, auth_settings=AuthSettings(origins=(ORIGIN,))), base_url=ORIGIN
    )
    restarted.cookies.update(alice.cookies)
    assert restarted.get(path).json()["granted"]
    assert alice.delete(path).status_code == 204
    assert alice.delete(path).status_code == 204
    assert not restarted.get(path).json()["granted"]
    assert TestClient(app, base_url=ORIGIN).get(path).status_code == 401
    assert alice.post(path, json={"notice_version": "groq_context_v1"}).status_code == 200
    with service.sessions.begin() as db:
        from app.storage.models import Conversation

        db.delete(db.get(Conversation, conversation))
    with service.sessions() as db:
        assert db.scalar(select(ExternalConsent)) is None


def test_synthetic_route_and_revocation_race(api):
    service, app, alice, _ = api
    _, run = accepted(alice)
    path = f"/api/v1/runs/{run}/external-consent"
    assert alice.post(path + "/synthetic-check").status_code == 503
    calls = []

    class Port:
        async def generate(self, *, system, data, timeout, cancel):
            calls.append(data)
            with service.sessions.begin() as db:
                row = db.scalar(select(ExternalConsent))
                db.delete(row)
            return {"result": "synthetic"}

    def factory(deadline, cancel):
        calls.append("factory")
        return Port()

    app.state.synthetic_guard_port = factory
    assert alice.post(path + "/synthetic-check").status_code == 503
    assert calls == []
    assert alice.post(path, json={"notice_version": "groq_context_v1"}).status_code == 200
    assert alice.post(path + "/synthetic-check").status_code == 503
    assert len(calls) == 2
    assert "a red test cube" in calls[1]
    assert not alice.get(path).json()["granted"]


def test_run_cancellation_drops_synthetic_response(api):
    service, app, alice, _ = api
    _, run = accepted(alice)
    path = f"/api/v1/runs/{run}/external-consent"
    assert alice.post(path, json={"notice_version": "groq_context_v1"}).status_code == 200
    calls = []

    class Port:
        async def generate(self, *, system, data, timeout, cancel):
            from app.storage.jobs import JobRepository

            calls.append("started")
            with service.sessions.begin() as db:
                from uuid import UUID

                owner = service.authenticate(alice.cookies.get("article_session"))
                JobRepository(db).request_cancel(UUID(run), owner_id=owner.user_id)
            try:
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                calls.append("cancelled")
                return {"result": "late"}
            return {"result": "late"}

    app.state.synthetic_guard_port = lambda deadline, cancel: Port()
    assert alice.post(path + "/synthetic-check").status_code == 409
    assert calls == ["started", "cancelled"]


def test_disconnected_client_cancels_synthetic_result(api):
    from uuid import UUID

    from fastapi import HTTPException

    from app.api.routes.consent import synthetic_check

    service, app, alice, _ = api
    _, run = accepted(alice)
    path = f"/api/v1/runs/{run}/external-consent"
    assert alice.post(path, json={"notice_version": "groq_context_v1"}).status_code == 200
    principal = service.authenticate(alice.cookies.get("article_session"))
    started = asyncio.Event()
    observed = []

    class Request:
        def __init__(self):
            self.app = app

        async def is_disconnected(self):
            return started.is_set()

    class Port:
        async def generate(self, *, system, data, timeout, cancel):
            started.set()
            try:
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                observed.append("cancelled")
                return {"result": "late"}

    app.state.synthetic_guard_port = lambda deadline, cancel: Port()

    async def scenario():
        with service.sessions() as db:
            with pytest.raises(HTTPException) as error:
                await synthetic_check(UUID(run), Request(), principal, db)
            assert error.value.status_code == 409

    asyncio.run(scenario())
    assert observed == ["cancelled"]


def test_real_synthetic_groq_port_with_mock_transport(api):
    import json
    from pathlib import Path

    import httpx

    runtime = pytest.importorskip("app.integrations.groq_runtime")
    _, app, alice, _ = api
    _, run = accepted(alice)
    path = f"/api/v1/runs/{run}/external-consent"
    requests = []
    providers = []

    def handler(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(503)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": json.dumps({"relation": "full"}),
                        },
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )

    class Local:
        async def embed(self, **kwargs):
            return []

        async def rerank(self, **kwargs):
            return []

    client = httpx.AsyncClient(
        base_url="https://api.groq.com", transport=httpx.MockTransport(handler)
    )

    def factory(deadline, cancel):
        provider = runtime.synthetic_provider(
            client,
            api_key="synthetic",
            path=Path("config/groq.example.yaml"),
            local=Local(),
            max_attempts=2,
        )
        providers.append(provider)
        return runtime.SyntheticGuardPort(provider, deadline=deadline, cancel=cancel)

    app.state.synthetic_guard_port = factory
    assert alice.post(path + "/synthetic-check").status_code == 503
    assert not providers and not requests
    assert alice.post(path, json={"notice_version": "groq_context_v1"}).status_code == 200
    response = alice.post(path + "/synthetic-check")
    assert response.status_code == 200, response.text
    assert response.json() == {"ok": True}
    assert len(requests) == 2
    assert providers[0].budget.requests == 2
    assert providers[0].budget.unknown_usage_attempts == 1
    assert providers[0].budget.known_input_tokens == 10
