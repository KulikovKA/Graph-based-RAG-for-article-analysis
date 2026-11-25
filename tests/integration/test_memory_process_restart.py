"""Перезапуск API и worker с изолированными PostgreSQL и Redis."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from app.services.auth import AuthService
from app.services.conversations import ConversationService
from app.services.memory import MemoryService
from app.storage.models import (
    AnalysisRun,
    DocumentRevision,
    EvidenceChunk,
    IndexCatalog,
    IndexGeneration,
    IndexMember,
    SourceDocument,
)
from app.storage.repositories import make_session_factory

pytest_plugins = ["tests.integration.test_repositories"]
pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL") or not os.getenv("TEST_REDIS_URL"),
    reason="isolated test PostgreSQL and Redis are required",
)


def test_api_worker_restart_history_snapshot_and_cache(engine, tmp_path):
    email, password = f"{uuid4()}@example.test", "fixture-password-123"
    auth = AuthService(make_session_factory(engine))
    owner = auth.create_account(email, password)
    owner_id = owner
    generation, document, revision, chunk = (uuid4() for _ in range(4))
    text = "The optical sensor measures reflected light."
    with Session(engine) as db, db.begin():
        db.add(IndexGeneration(id=generation, config_versions_json={}))
        db.add(
            SourceDocument(
                id=document,
                source="openalex",
                external_id=str(document),
                canonical_url="https://example.test/source",
                kind="article",
                title="Fixture",
            )
        )
        db.flush()
        db.add(
            DocumentRevision(
                id=revision,
                document_id=document,
                content_hash="a" * 64,
                normalized_json={},
                ingest_state="indexed",
            )
        )
        db.add(IndexCatalog(id=1, current_generation_id=generation))
        db.flush()
        db.add(
            EvidenceChunk(
                id=chunk,
                revision_id=revision,
                section="abstract",
                ordinal=0,
                text=text,
                section_start=0,
                section_end=len(text),
                hash=hashlib.sha256(text.encode()).hexdigest(),
                language="en",
            )
        )
        db.add(IndexMember(generation_id=generation, document_id=document, revision_id=revision))
    env = dict(
        os.environ,
        FIXTURE_DATABASE_URL=str(engine.url),
        FIXTURE_SECRET=str(uuid4()),
        FIXTURE_TRACE=str(tmp_path / "trace.jsonl"),
        PYTHONPATH=str(Path.cwd() / "src"),
    )

    def child(role, payload):
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "tests.integration.memory_process_fixture",
                role,
                json.dumps(payload),
            ],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
        assert proc.returncode == 0, proc.stderr + proc.stdout
        return json.loads(proc.stdout.strip().splitlines()[-1]), proc.stderr

    def api(method, path, body=None, headers=None):
        result, _ = child(
            "api",
            {
                "email": email,
                "password": password,
                "method": method,
                "path": path,
                "body": body,
                "headers": headers or {},
            },
        )
        return result

    created = api("POST", "/api/v1/conversations", {})
    assert created["status"] == 201
    chat = created["body"]["id"]

    def submit(version, source=None):
        body = {"content": "optical sensor", "expected_idea_version": version, "analyze": True}
        if source:
            body["source_run_id"] = source
        response = api(
            "POST",
            f"/api/v1/conversations/{chat}/messages",
            body,
            {"Idempotency-Key": str(uuid4())},
        )
        assert response["status"] == 202, response
        return response

    first = submit(0)
    worker1, log1 = child("worker", {})
    assert worker1["processed"]
    assert "stage=retrieval outcome=miss" in log1 and "stage=rerank outcome=miss" in log1, (
        worker1,
        log1,
    )
    with Session(engine) as db, db.begin():
        run = db.get(AnalysisRun, UUID(first["body"]["run_id"]))
        if run.status != "completed":
            pytest.fail(log1, pytrace=False)
        assert run.evidence_snapshot_json["sources"]
        old_snapshot = run.evidence_snapshot_json
        old_version = run.idea_version_id
        conversation = ConversationService(db)
        for i in range(12):
            conversation.append_message(owner_id, UUID(chat), role="user", content=f"history-{i}")
        messages = conversation.messages(owner_id, UUID(chat))
        conversation.set_summary(
            owner_id, UUID(chat), {"text": "legacy-summary-marker"}, messages[0].id
        )
    second = submit(1)
    worker2, log2 = child("worker", {})
    assert worker2["processed"] and worker2["pid"] != worker1["pid"]
    assert "stage=retrieval outcome=hit" in log2 and "stage=rerank outcome=hit" in log2
    with Session(engine) as db, db.begin():
        run2 = db.get(AnalysisRun, UUID(second["body"]["run_id"]))
        assert run2.status == "completed"
        memory = MemoryService(db).context(owner_id, UUID(chat))
        assert memory.summary["schema_version"] == 1
        checkpoint = memory.summary_until_message_id
        assert checkpoint is not None
        gen2 = uuid4()
        db.add(IndexGeneration(id=gen2, config_versions_json={}))
        db.flush()
        db.get(IndexCatalog, 1).current_generation_id = gen2
        db.add(IndexMember(generation_id=gen2, document_id=document, revision_id=revision))
    followup = submit(1, first["body"]["run_id"])
    worker3, log3 = child("worker", {})
    assert worker3["processed"] and worker3["pid"] not in {worker1["pid"], worker2["pid"]}
    assert "stage=retrieval" not in log3
    with Session(engine) as db:
        run3 = db.get(AnalysisRun, UUID(followup["body"]["run_id"]))
        assert run3.status == "completed"
        assert run3.evidence_snapshot_json == old_snapshot
        assert run3.idea_version_id == old_version
        assert run3.index_generation_id == generation
        memory = MemoryService(db).context(owner_id, UUID(chat))
        assert memory.summary_until_message_id is not None
        messages = ConversationService(db).messages(owner_id, UUID(chat))
        positions = {m.id: i for i, m in enumerate(messages)}
        assert positions[memory.summary_until_message_id] >= positions[checkpoint]
    fourth = submit(1)
    worker4, log4 = child("worker", {})
    assert worker4["processed"] and worker4["pid"] not in {
        worker1["pid"],
        worker2["pid"],
        worker3["pid"],
    }
    assert "stage=retrieval outcome=miss" in log4 and "stage=rerank outcome=miss" in log4
    with Session(engine) as db:
        assert db.get(AnalysisRun, UUID(fourth["body"]["run_id"])).status == "completed"
    history = api("GET", f"/api/v1/conversations/{chat}/messages")
    assert history["pid"] != created["pid"] and history["status"] == 200
    assert any(m["content"] == "history-0" for m in history["body"]["items"])
    traces = [
        json.loads(line)["summary"] for line in (tmp_path / "trace.jsonl").read_text().splitlines()
    ]
    assert "legacy-summary-marker" in traces[1]
    assert "history-0" in traces[2]
