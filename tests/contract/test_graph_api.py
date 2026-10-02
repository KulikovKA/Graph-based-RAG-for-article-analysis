"""GraphV1 is bounded and every read is scoped to the owning run."""

import hashlib
import os
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.auth import AuthSettings
from app.main import create_app
from app.services.auth import AuthService
from app.storage.jobs import JobRepository
from app.storage.repositories import make_session_factory

pytest_plugins = ["tests.integration.test_repositories"]

pytestmark = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="no PostgreSQL test DB")
PASSWORD = "synthetic-graph-password"
ORIGIN = "https://graph.example.test"


def test_graph_api_owner_scope_and_bounds(engine) -> None:  # type: ignore[no-untyped-def]
    service = AuthService(make_session_factory(engine))
    service.create_account("graph-a@example.test", PASSWORD)
    service.create_account("graph-b@example.test", PASSWORD)
    app = create_app(auth=service, auth_settings=AuthSettings(origins=(ORIGIN,)))
    clients = [TestClient(app, base_url=ORIGIN), TestClient(app, base_url=ORIGIN)]
    for client, email in zip(
        clients, ("graph-a@example.test", "graph-b@example.test"), strict=True
    ):
        login = client.post(
            "/api/v1/auth/login",
            headers={"Origin": ORIGIN},
            json={"email": email, "password": PASSWORD},
        )
        client.headers.update({"Origin": ORIGIN, "X-CSRF-Token": login.json()["csrf_token"]})
    owner, other = clients
    conversation = owner.post("/api/v1/conversations", json={}).json()["id"]
    run_id = owner.post(
        f"/api/v1/conversations/{conversation}/messages",
        headers={"Idempotency-Key": str(uuid4())},
        json={"content": "idea", "expected_idea_version": 0, "analyze": True},
    ).json()["run_id"]
    with service.sessions.begin() as db:
        lease = JobRepository(db).claim_next(worker="graph-test", duration=timedelta(minutes=1))
        assert lease is not None
        assert JobRepository(db).complete(
            lease.run_id,
            worker="graph-test",
            token=lease.token,
            outcome="no_evidence",
            answer={
                "schema_version": 1,
                "summary": [],
                "matches": [],
                "differences": [],
                "limitations": [],
                "followup_suggestions": [],
            },
            public_analysis={"schema_version": 1, "items": [], "limitations": []},
            answer_presentation={
                "schema_version": 1,
                "renderer_version": "test-v1",
                "text": "",
                "presentation_id": hashlib.sha256(b"test-v1").hexdigest(),
                "text_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "chunk_count": 1,
            },
            coverage={"sources": [], "channels": [], "partial": False, "historical": False},
        )
    detail = owner.get(f"/api/v1/runs/{run_id}").json()
    assert detail["graph_url"].endswith(f"/runs/{run_id}/graph")
    graph = owner.get(detail["graph_url"]).json()
    assert len(graph["nodes"]) <= 30 and len(graph["edges"]) <= 50
    assert graph["run_id"] == run_id
    assert other.get(detail["graph_url"]).status_code == 404
    root_id = graph["nodes"][0]["id"]
    expanded = owner.get(f"/api/v1/runs/{run_id}/graph/neighbors", params={"node_id": root_id})
    assert expanded.status_code == 200
    assert len(expanded.json()["nodes"]) <= 100 and len(expanded.json()["edges"]) <= 20
    assert (
        owner.get(
            f"/api/v1/runs/{run_id}/graph/neighbors", params={"node_id": root_id, "limit": 21}
        ).status_code
        == 422
    )
    assert (
        owner.get(
            f"/api/v1/runs/{run_id}/graph/neighbors", params={"node_id": "internal:neo4j-id"}
        ).status_code
        == 404
    )
    assert (
        owner.get(
            f"/api/v1/runs/{run_id}/graph/neighbors",
            params={"node_id": graph["nodes"][0]["id"], "cursor": "tampered"},
        ).status_code
        == 400
    )
