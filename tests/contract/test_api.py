"""Контракт API на PostgreSQL: изоляция, публикация и восстановление SSE."""

import asyncio
import hashlib
import json
import os
import threading
import time
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from tests.integration import test_repositories

from app.api.auth import AuthSettings
from app.api.dependencies import database
from app.api.routes.runs import BoundedStreamingResponse, replay_batch, stream
from app.api.schemas import EVENT_SCHEMAS
from app.domain.contracts import AnswerV1, PublicAnalysisV1
from app.main import create_app
from app.services.auth import AuthService
from app.services.run_events import RunEventsService
from app.storage.jobs import JobRepository
from app.storage.models import (
    AnalysisRun,
    DocumentRevision,
    EvidenceChunk,
    RunEvidence,
    SourceDocument,
)
from app.storage.repositories import make_session_factory

engine = test_repositories.engine
ORIGIN = "https://api.example.test"
PASSWORD = "synthetic-api-password"


@pytest.fixture
def api(engine):  # type: ignore[no-untyped-def] # noqa: F811
    service = AuthService(make_session_factory(engine))
    service.create_account("alice@example.test", PASSWORD)
    service.create_account("bob@example.test", PASSWORD)
    app = create_app(auth=service, auth_settings=AuthSettings(origins=(ORIGIN,)))
    alice, bob = TestClient(app, base_url=ORIGIN), TestClient(app, base_url=ORIGIN)
    for client, email in ((alice, "alice@example.test"), (bob, "bob@example.test")):
        response = client.post(
            "/api/v1/auth/login",
            headers={"Origin": ORIGIN},
            json={"email": email, "password": PASSWORD},
        )
        assert response.status_code == 200
        client.headers.update({"Origin": ORIGIN, "X-CSRF-Token": response.json()["csrf_token"]})
    return service, app, alice, bob


def accepted(client: TestClient) -> tuple[str, str]:
    conversation = client.post("/api/v1/conversations", json={"title": "Идея"}).json()["id"]
    response = client.post(
        f"/api/v1/conversations/{conversation}/messages",
        headers={"Idempotency-Key": str(uuid4())},
        json={"content": "Новая идея", "expected_idea_version": 0, "analyze": True},
    )
    assert response.status_code == 202, response.text
    return conversation, response.json()["run_id"]


def complete(service: AuthService, run_id: str) -> None:
    with service.sessions.begin() as db:
        lease = JobRepository(db).claim_next(worker="test", duration=timedelta(minutes=1))
        assert lease is not None and str(lease.run_id) == run_id
        text = "Проверенный ответ 🙂. " * 60
        presentation = {
            "schema_version": 1,
            "renderer_version": "test-v1",
            "text": text,
            "presentation_id": hashlib.sha256(("test-v1" + text).encode()).hexdigest(),
            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "chunk_count": (len(text) + 1023) // 1024,
        }
        assert JobRepository(db).complete(
            lease.run_id,
            worker="test",
            token=lease.token,
            outcome="no_evidence",
            answer=AnswerV1(
                summary=[], matches=[], differences=[], limitations=[], followup_suggestions=[]
            ).model_dump(mode="json"),
            public_analysis=PublicAnalysisV1(items=[], limitations=[]).model_dump(mode="json"),
            answer_presentation=presentation,
            coverage={"sources": [], "channels": [], "partial": False, "historical": False},
        )


postgres = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="no PostgreSQL test DB")


@postgres
def test_accept_conflicts_and_owner_before_reads(api) -> None:  # type: ignore[no-untyped-def]
    service, _, alice, bob = api
    conversation, run = accepted(alice)
    detail = alice.get(f"/api/v1/runs/{run}").json()
    assert detail["status"] == "pending" and detail["answer"] is None
    assert detail["progress"]["attempt"] == 0 and detail["graph_url"] is None
    response = alice.post(
        f"/api/v1/conversations/{conversation}/messages",
        headers={"Idempotency-Key": "other"},
        json={"content": "follow-up", "expected_idea_version": 0, "analyze": True},
    )
    assert response.status_code == 409 and response.json()["error"]["code"] == "RUN_IN_PROGRESS"
    for path in (
        f"conversations/{conversation}",
        f"conversations/{conversation}/messages",
        f"runs/{run}",
        f"runs/{run}/events",
        f"runs/{run}/evidence/{uuid4()}",
    ):
        assert bob.get("/api/v1/" + path).status_code == 404
    assert bob.post(f"/api/v1/runs/{run}/cancel").status_code == 404
    assert bob.get("/api/v1/conversations").json()["items"] == []
    with service.sessions() as db:
        stored = db.scalar(select(AnalysisRun).where(AnalysisRun.id == run))
        key = stored.idempotency_key
    same = alice.post(
        f"/api/v1/conversations/{conversation}/messages",
        headers={"Idempotency-Key": key},
        json={"content": "Новая идея", "expected_idea_version": 0, "analyze": True},
    )
    assert same.json()["run_id"] == run
    changed = alice.post(
        f"/api/v1/conversations/{conversation}/messages",
        headers={"Idempotency-Key": key},
        json={"content": "Другая идея", "expected_idea_version": 0, "analyze": True},
    )
    assert changed.status_code == 409 and changed.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


@postgres
def test_sse_replay_reset_terminal_cursor_and_cancel(api) -> None:  # type: ignore[no-untyped-def]
    service, _, alice, _ = api
    _, run = accepted(alice)
    complete(service, run)
    dto = alice.get(f"/api/v1/runs/{run}").json()
    assert dto["status"] == "completed" and dto["public_analysis"] is not None
    response = alice.get(f"/api/v1/runs/{run}/events")
    assert response.status_code == 200 and response.headers["content-type"].startswith(
        "text/event-stream"
    )
    envelopes = [
        json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")
    ]
    deltas = [item["payload"]["text"] for item in envelopes if "chunk_index" in item["payload"]]
    assert "".join(deltas) == dto["answer_presentation"]["text"]
    terminal = envelopes[-1]["seq"]
    assert envelopes[-1]["payload"]["run"] == dto
    assert (
        alice.get(f"/api/v1/runs/{run}/events", headers={"Last-Event-ID": str(terminal)}).text == ""
    )
    for value in (str(terminal + 1), "-1", "bad"):
        assert (
            alice.get(f"/api/v1/runs/{run}/events", headers={"Last-Event-ID": value}).status_code
            == 400
        )
    replay = alice.get(f"/api/v1/runs/{run}/events", headers={"Last-Event-ID": "1"})
    assert "id: 1\n" not in replay.text and "event: completed" in replay.text
    cancel = alice.post(f"/api/v1/runs/{run}/cancel")
    assert cancel.status_code == 200 and cancel.json()["status"] == "completed"
    with service.sessions.begin() as db:
        RunEventsService(db).compact(terminal_before=datetime.now(UTC) + timedelta(seconds=1))
    reset = alice.get(f"/api/v1/runs/{run}/events").text
    assert "event: run_snapshot" in reset and '"reset":true' in reset
    assert "event: answer_delta" not in reset


@postgres
def test_inputs_versions_sources_pagination_and_revocation(api) -> None:  # type: ignore[no-untyped-def]
    service, _, alice, _ = api
    conversation, run = accepted(alice)
    for body, status in (
        ({"content": "я" * 4097, "expected_idea_version": 0, "analyze": True}, 413),
        ({"content": "secret-sentinel", "expected_idea_version": 0, "analyze": False}, 422),
    ):
        response = alice.post(
            f"/api/v1/conversations/{conversation}/messages",
            headers={"Idempotency-Key": "oversize"},
            json=body,
        )
        assert response.status_code == status and "secret-sentinel" not in response.text
    assert alice.post("/api/v1/conversations", content="x" * 16385).status_code == 413
    assert alice.get("/api/v1/conversations", params={"cursor": "bad"}).status_code == 400
    alice.post("/api/v1/conversations", json={"title": "Ещё"})
    page = alice.get("/api/v1/conversations?limit=1").json()
    next_page = alice.get(
        "/api/v1/conversations", params={"limit": 1, "cursor": page["next_cursor"]}
    ).json()
    assert page["items"][0]["id"] != next_page["items"][0]["id"]
    other = alice.post("/api/v1/conversations", json={}).json()["id"]
    assert (
        alice.post(
            f"/api/v1/conversations/{other}/messages",
            headers={"Idempotency-Key": "src"},
            json={
                "content": "источник",
                "expected_idea_version": 0,
                "source_run_id": run,
                "analyze": True,
            },
        ).status_code
        == 404
    )
    complete(service, run)
    assert (
        alice.post(
            f"/api/v1/conversations/{conversation}/messages",
            headers={"Idempotency-Key": "version"},
            json={"content": "новая", "expected_idea_version": 1, "analyze": True},
        ).json()["error"]["code"]
        == "VERSION_CONFLICT"
    )
    service.disable_account("alice@example.test")
    assert alice.get(f"/api/v1/runs/{run}/events").status_code == 401


@postgres
def test_evidence_snapshot_and_no_private_draft(api) -> None:  # type: ignore[no-untyped-def]
    service, _, alice, bob = api
    _, run = accepted(alice)
    document, revision, chunk, evidence_id = uuid4(), uuid4(), uuid4(), uuid4()
    with service.sessions.begin() as db:
        db.add(
            SourceDocument(
                id=document,
                source="openalex",
                external_id="W1",
                kind="article",
                title="Источник",
                canonical_url="https://openalex.org/W1",
            )
        )
        db.flush()
        db.add(
            DocumentRevision(
                id=revision,
                document_id=document,
                content_hash="c" * 64,
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
                text="Цитата",
                language="ru",
                section_start=0,
                section_end=6,
                hash="d" * 64,
            )
        )
        db.flush()
        db.add(
            RunEvidence(
                run_id=run,
                evidence_id=evidence_id,
                document_id=document,
                revision_id=revision,
                chunk_id=chunk,
                span_start=0,
                span_end=6,
                quoted_span="Цитата",
                source_url="https://openalex.org/W1",
            )
        )
        saved = db.scalar(select(AnalysisRun).where(AnalysisRun.id == run))
        saved.config_versions_json = {"private": "RAW_REASONING_SENTINEL"}
    assert "RAW_REASONING_SENTINEL" not in alice.get(f"/api/v1/runs/{run}").text
    route = f"/api/v1/runs/{run}/evidence/{evidence_id}"
    assert alice.get(route).json()["quoted_span"] == "Цитата"
    assert bob.get(route).status_code == 404
    assert alice.get(f"/api/v1/runs/{uuid4()}/evidence/{evidence_id}").status_code == 404
    metadata = bob.get(f"/api/v1/sources/{document}").json()
    assert "evidence_id" not in metadata and "run_id" not in metadata


@postgres
def test_live_stream_rechecks_session_and_stale_cursor(api) -> None:  # type: ignore[no-untyped-def]
    service, _, alice, _ = api
    _, run = accepted(alice)
    token = alice.cookies.get("article_session")
    owner = service.authenticate(token)
    from uuid import UUID

    initial = replay_batch(service, owner, token, UUID(run), None)

    async def check() -> None:
        iterator = stream(service, owner, token, UUID(run), None, initial)
        assert b"event: run_started" in await anext(iterator)
        service.disable_account("alice@example.test")
        with pytest.raises(StopAsyncIteration):
            await anext(iterator)

    asyncio.run(check())


def test_backpressure_timeout_closes_iterator() -> None:
    closed: list[bool] = []

    async def body():  # type: ignore[no-untyped-def]
        try:
            yield b"first"
            yield b"second"
        finally:
            closed.append(True)

    async def blocked_send(message: Any) -> None:
        if message["type"] == "http.response.body":
            await asyncio.sleep(1)

    async def check() -> None:
        response = BoundedStreamingResponse(body())
        response.send_timeout = 0.01
        await response.stream_response(blocked_send)

    asyncio.run(check())
    assert closed == [True]


def test_openapi_snapshot_has_only_public_dtos() -> None:
    schema = create_app().openapi()
    assert "AnalysisV1" not in schema["components"]["schemas"]
    assert schema == json.loads(Path("tests/fixtures/api/openapi.json").read_text(encoding="utf-8"))


def test_sse_fixture_matches_typed_payloads() -> None:
    fixture = json.loads(Path("tests/fixtures/api/sse.json").read_text(encoding="utf-8"))
    for event in fixture:
        schema = EVENT_SCHEMAS[event["event"]]
        schema.model_validate(event["payload"])
        with pytest.raises(ValueError):
            schema.model_validate({**event["payload"], "analysis": "RAW_REASONING_SENTINEL"})


@postgres
def test_queue_unavailable_and_active_cancel(api) -> None:  # type: ignore[no-untyped-def]
    _, app, alice, _ = api
    conversation, run = accepted(alice)
    response = alice.post(f"/api/v1/runs/{run}/cancel")
    assert response.status_code == 202 and response.json()["cancel_requested"]

    def unavailable() -> None:
        raise SQLAlchemyError("PRIVATE_DATABASE_SENTINEL")

    app.dependency_overrides[database] = unavailable
    response = alice.post(
        f"/api/v1/conversations/{conversation}/messages",
        headers={"Idempotency-Key": "unavailable"},
        json={"content": "идея", "expected_idea_version": 0, "analyze": True},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "QUEUE_UNAVAILABLE"
    assert "PRIVATE_DATABASE_SENTINEL" not in response.text


@postgres
def test_real_caddy_flush_before_terminal_commit(api) -> None:  # type: ignore[no-untyped-def]
    proxy = os.getenv("TEST_PROXY_URL")
    if not proxy:
        pytest.skip("TEST_PROXY_URL is not configured")
    service, app, _, _ = api
    app.state.auth_settings = replace(
        app.state.auth_settings, origins=(proxy,), http_dev_enabled=True, cookie_secure=False
    )
    server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    try:
        while not server.started:
            assert time.monotonic() < deadline
            time.sleep(0.01)
        with httpx.Client(
            base_url=proxy, timeout=3, headers={"Origin": proxy, "Accept-Encoding": "identity"}
        ) as client:
            auth = client.post(
                "/api/v1/auth/login", json={"email": "alice@example.test", "password": PASSWORD}
            )
            assert auth.status_code == 200
            client.headers["X-CSRF-Token"] = auth.json()["csrf_token"]
            conversation = client.post("/api/v1/conversations", json={}).json()["id"]
            run = client.post(
                f"/api/v1/conversations/{conversation}/messages",
                headers={"Idempotency-Key": "proxy"},
                json={"content": "Идея через Caddy", "expected_idea_version": 0, "analyze": True},
            ).json()["run_id"]
            started = time.monotonic()
            with client.stream("GET", f"/api/v1/runs/{run}/events") as response:
                lines = response.iter_lines()
                assert next(lines) == "id: 1"
                assert time.monotonic() - started < 2
                # Первый frame уже виден до появления terminal commit.
                assert client.get(f"/api/v1/runs/{run}").json()["status"] == "pending"
                complete(service, run)
                received = "\n".join(lines)
                assert "event: completed" in received and "event: answer_delta" in received
    finally:
        server.should_exit = True
        thread.join(timeout=5)
