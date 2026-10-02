"""Gate AUTH-002: Origin, TLS-конфигурация, SSRF и отзыв защищённого доступа."""

# ruff: noqa: F811

import asyncio
from dataclasses import replace
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
import yaml
from fastapi.testclient import TestClient
from scripts.audit_perimeter import violations
from tests.contract.test_api import accepted, postgres
from tests.contract.test_api import api as api  # noqa: F401
from tests.contract.test_api import engine as engine  # noqa: F401
from tests.security.test_isolation import CONFIG, ORIGIN, client_for, login
from tests.security.test_isolation import service as service  # noqa: F401

from app.api.auth import COOKIE_NAME
from app.api.routes.runs import stream
from app.domain.source import SourceStatus
from app.integrations.epo import EpoOpsClient
from app.integrations.openalex import OpenAlexClient
from app.services.auth import AuthService
from app.services.run_events import StoredEvent
from app.storage.models import DocumentRevision, EvidenceChunk, RunEvidence, SourceDocument, utcnow

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("origin", ["null", "https://evil.test", ORIGIN + "/", ORIGIN + ".evil"])
def test_rejected_origin_cannot_read_or_preflight(service: AuthService, origin: str) -> None:
    client = client_for(service)
    login(client)
    for method in ("GET", "OPTIONS"):
        response = client.request(
            method,
            "/api/v1/auth/session",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 403
        assert "access-control-allow-origin" not in response.headers
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-request-id"]


def test_exact_cors_allowlist_and_csrf(service: AuthService) -> None:
    client = client_for(service)
    session = login(client)
    response = client.options(
        "/api/v1/auth/logout",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-CSRF-Token,Content-Type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"
    assert client.get("/api/v1/auth/session", headers={"Origin": ORIGIN}).status_code == 200
    assert client.post("/api/v1/auth/logout", headers={"Origin": ORIGIN}).status_code == 403
    assert (
        client.post(
            "/api/v1/auth/logout",
            headers={
                "Origin": ORIGIN,
                "X-CSRF-Token": session["csrf_token"],
            },
        ).status_code
        == 204
    )
    assert client.get("/api/v1/auth/session").status_code == 401
    response = client.get("/api/v1/auth/session", headers=[("Origin", ORIGIN), ("Origin", ORIGIN)])
    assert response.status_code == 403


def test_rate_limit_shared_between_api_instances(service: AuthService) -> None:
    config = replace(CONFIG, request_user_limit=1)
    first = client_for(service, config)
    login(first)
    second = client_for(AuthService(service.sessions), config)
    second.cookies.update(first.cookies)
    assert first.get("/api/v1/auth/session").status_code == 200
    response = second.get("/api/v1/auth/session")
    assert response.status_code == 429 and int(response.headers["retry-after"]) > 0


@pytest.mark.parametrize(
    "target",
    [
        "http://127.0.0.1/",
        "https://localhost/",
        "https://[::1]/",
        "https://169.254.169.254/latest/meta-data/",
        "https://postgres:5432/",
        "https://api.openalex.org.evil.test/works/W123",
        "//api.openalex.org/works/W123",
        "https://api.openalex.org@127.0.0.1/works/W123",
    ],
)
@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_source_redirect_never_fetches_internal_url(target: str, status: int) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.path.endswith("/auth/accesstoken"):
            return httpx.Response(200, json={"access_token": "synthetic", "expires_in": 3600})
        return httpx.Response(status, headers={"Location": target})

    async def scenario() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=True
        ) as http:
            assert (await OpenAlexClient(http).fetch("W123")).status == SourceStatus.UNAVAILABLE
            assert (
                await EpoOpsClient(http, consumer_key="test", consumer_secret="test").search(
                    "sensor"
                )
            ).status == SourceStatus.UNAVAILABLE
            for adapter, value in (
                (OpenAlexClient(http), target),
                (EpoOpsClient(http, consumer_key="test", consumer_secret="test"), target),
            ):
                with pytest.raises(ValueError):
                    await adapter.fetch(value)

    asyncio.run(scenario())
    assert len(calls) == 3
    assert all(r.url.host in {"api.openalex.org", "ops.epo.org"} for r in calls)


def test_revocation_stops_already_open_sse(service: AuthService) -> None:
    client = client_for(service)
    login(client)
    token = client.cookies.get(COOKIE_NAME)
    owner = service.authenticate(token)
    assert owner is not None
    run_id = uuid4()
    events = [
        StoredEvent(
            run_id,
            seq,
            "verification",
            {
                "schema_version": 1,
                "phase": "started",
                "scope": "result",
            },
            utcnow(),
        )
        for seq in (1, 2)
    ]

    async def scenario() -> None:
        iterator = stream(service, owner, token, run_id, None, (events, False))
        assert b"id: 1" in await anext(iterator)
        service.logout(owner)
        with pytest.raises(StopAsyncIteration):
            await anext(iterator)

    asyncio.run(scenario())


@postgres
@pytest.mark.parametrize("revoke", ["rotate", "logout", "disable"])
def test_revoked_cookie_cannot_read_sse_or_evidence(api, revoke: str) -> None:  # type: ignore[no-untyped-def] # noqa: F811
    auth, app, alice, _ = api
    _, run = accepted(alice)
    document, revision, chunk, evidence_id = (uuid4() for _ in range(4))
    with auth.sessions.begin() as db:
        db.add(
            SourceDocument(
                id=document,
                source="openalex",
                external_id="W123",
                kind="article",
                title="Тест",
                canonical_url="https://openalex.org/W123",
            )
        )
        db.flush()
        db.add(
            DocumentRevision(
                id=revision,
                document_id=document,
                content_hash="a" * 64,
                normalized_json={},
                ingest_state="normalized",
            )
        )
        db.flush()
        db.add(
            EvidenceChunk(
                id=chunk,
                revision_id=revision,
                section="abstract",
                ordinal=0,
                text="Тест",
                language="ru",
                section_start=0,
                section_end=4,
                hash="b" * 64,
            )
        )
        db.flush()
        db.add(
            RunEvidence(
                run_id=UUID(run),
                evidence_id=evidence_id,
                document_id=document,
                revision_id=revision,
                chunk_id=chunk,
                span_start=0,
                span_end=4,
                quoted_span="Тест",
                source_url="https://openalex.org/W123",
            )
        )
    assert alice.get(f"/api/v1/runs/{run}/evidence/{evidence_id}").status_code == 200
    token = alice.cookies.get(COOKIE_NAME)
    if revoke == "rotate":
        assert auth.login("alice@example.test", "synthetic-api-password", token)
    elif revoke == "disable":
        auth.disable_account("alice@example.test")
    else:
        principal = auth.authenticate(token)
        assert principal is not None
        auth.logout(principal)
    stale = TestClient(app, base_url="https://api.example.test")
    stale.cookies.set(COOKIE_NAME, token)
    for path in (f"runs/{run}/events", f"runs/{run}/evidence/{evidence_id}"):
        assert stale.get("/api/v1/" + path).status_code == 401


def test_compose_publishes_only_caddy_and_pins_tls() -> None:
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))
    for name, config in compose["services"].items():
        assert config.get("network_mode") != "host"
        if config.get("ports"):
            assert name in {"caddy-dev", "caddy-prod"}
            assert all("127.0.0.1" in port for port in config["ports"])
    assert compose["networks"]["backend"]["internal"] is True
    prod = (ROOT / "docker/Caddyfile.prod").read_text(encoding="utf-8")
    assert "protocols tls1.2 tls1.3" in prod
    assert 'Strict-Transport-Security "max-age=31536000"' in prod
    assert "tls internal" not in prod
    assert "admin off" in prod
    assert "Strict-Transport-Security" not in (ROOT / "Caddyfile").read_text()


def test_live_audit_detects_overrides_and_other_public_databases() -> None:
    def container(service: str, host: str, project: str = "article-analysis") -> dict:
        return {
            "name": service,
            "labels": {
                "com.docker.compose.project": project,
                "com.docker.compose.service": service,
            },
            "ports": {
                "443/tcp" if service == "caddy-prod" else "5432/tcp": [
                    {"HostIp": host, "HostPort": "8443" if service == "caddy-prod" else "5432"}
                ]
            },
        }

    assert not violations([container("caddy-prod", "0.0.0.0")])
    assert len(violations([container("postgres", "127.0.0.1")])) == 1
    assert len(violations([container("postgres", "0.0.0.0", "other")])) == 1
    assert not violations([container("postgres", "127.0.0.1", "other")])
    host_network = container("api", "127.0.0.1")
    host_network.update(network_mode="host", ports={})
    assert violations([host_network])[0]["reason"] == "host_network"
