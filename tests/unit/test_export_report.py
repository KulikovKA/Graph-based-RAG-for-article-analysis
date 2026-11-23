"""Компонентные проверки экспорта на сохранённых данных."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.auth import AuthSettings
from app.api.routes import runs
from app.main import create_app
from app.services.export_report import render_export


class FakeDB:
    def __init__(self, version, rows):
        self.version, self.rows = version, rows

    def scalar(self, query):
        return self.version

    def execute(self, query):
        return self

    def all(self):
        return self.rows


def fixture():
    run_id, owner, conv, ver, doc, rev, chunk_id, eid, feature = [uuid4() for _ in range(9)]
    url = "https://openalex.org/W1"
    text = "Точное <script> evidence"
    prefix = "?? "
    start, end = len(prefix), len(prefix) + len(text)
    item = SimpleNamespace(
        run_id=run_id,
        evidence_id=eid,
        document_id=doc,
        revision_id=rev,
        chunk_id=chunk_id,
        span_start=start,
        span_end=end,
        quoted_span=text,
        source_url=url,
    )
    chunk = SimpleNamespace(revision_id=rev, text=prefix + text, section="abstract", language="ru")
    entry = {
        key: str(getattr(item, key))
        for key in ("evidence_id", "document_id", "revision_id", "chunk_id")
    }
    entry.update(
        span_start=start,
        span_end=end,
        quoted_span=text,
        canonical_url=url,
        section="abstract",
        language="ru",
    )
    claim = {
        "text": "<script>вывод</script>",
        "evidence_ids": [str(eid)],
        "quotes": [{"evidence_id": str(eid), "start": start, "end": end, "text": text}],
    }
    run = SimpleNamespace(
        id=run_id,
        owner_user_id=owner,
        conversation_id=conv,
        idea_version_id=ver,
        source_run_id=None,
        index_generation_id=uuid4(),
        config_versions_json={"private": "SECRET_SENTINEL"},
        status="completed",
        stage="completed",
        outcome="analysis",
        answer_json={
            "schema_version": 1,
            "summary": [claim],
            "matches": [{"feature_id": str(feature), "document_id": str(doc), "claims": [claim]}],
            "differences": [],
            "limitations": [{"code": "PARTIAL", "message": "границы"}],
            "followup_suggestions": [],
        },
        public_analysis_json=None,
        answer_presentation_json=None,
        evidence_snapshot_json={
            "evidence": [entry],
            "sources": [
                {
                    "document_id": str(doc),
                    "revision_id": str(rev),
                    "title": "<img src=x>",
                    "kind": "patent",
                    "url": url,
                    "evidence_ids": [str(eid)],
                }
            ],
        },
        coverage_json={"sources": [], "channels": [], "partial": True, "historical": True},
        progress_json={},
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        error_code=None,
    )
    version = SimpleNamespace(
        version_no=2,
        normalized_json={
            "features": [{"id": str(feature), "text": "исторический признак", "weight": 1.0}]
        },
    )
    return run, FakeDB(version, [(item, chunk)])


def test_historical_snapshot_and_safe_html():
    run, db = fixture()
    html = render_export(db, run)
    assert "Отчёт исследования" in html and "SECRET_SENTINEL" not in html
    assert "исторический признак" in html and str(run.index_generation_id) in html
    assert str(db.rows[0][0].revision_id) in html and "Точное &lt;script&gt; evidence" in html
    assert "&lt;img src=x&gt;" in html and "<script>" not in html
    assert "границы" in html and "historical" in html


@pytest.mark.parametrize(
    "mutation",
    ["quote", "revision", "url", "missing", "feature", "quote_start", "quote_end", "span_end"],
)
def test_invalid_snapshot_fails_closed(mutation):
    run, db = fixture()
    if mutation == "quote":
        run.answer_json["summary"][0]["quotes"][0]["text"] = "подмена"
    elif mutation == "revision":
        run.evidence_snapshot_json["evidence"][0]["revision_id"] = str(uuid4())
    elif mutation == "url":
        run.evidence_snapshot_json["sources"][0]["url"] = "https://evil.example/"
    elif mutation == "missing":
        run.answer_json["summary"][0]["evidence_ids"] = [str(uuid4())]
    elif mutation == "quote_start":
        run.answer_json["summary"][0]["quotes"][0]["start"] -= 1
    elif mutation == "quote_end":
        run.answer_json["summary"][0]["quotes"][0]["end"] += 1
    elif mutation == "span_end":
        db.rows[0][0].span_end += 1
    else:
        run.answer_json["matches"][0]["feature_id"] = str(uuid4())
    with pytest.raises((ValueError, HTTPException)):
        render_export(db, run)


def test_empty_legacy_report():
    run, db = fixture()
    run.idea_version_id = None
    run.outcome = "no_evidence"
    run.answer_json = {
        "summary": [],
        "matches": [],
        "differences": [],
        "limitations": [],
        "followup_suggestions": ["Уточните вопрос"],
    }
    run.evidence_snapshot_json = {"sources": []}
    db.rows = []
    assert "no_evidence" in render_export(db, run)


def test_endpoint_status_and_attachment(monkeypatch):
    run, db = fixture()

    class Repo:
        def __init__(self, db):
            pass

        def get_run(self, run_id, *, owner_id):
            return run if run.id == run_id and run.owner_user_id == owner_id else None

    monkeypatch.setattr(runs, "OwnedRepository", Repo)
    owner = SimpleNamespace(user_id=run.owner_user_id)
    response = runs.export_run(run.id, owner, db)
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    assert response.headers["content-disposition"] == f'attachment; filename="run-{run.id}.html"'
    assert response.headers["content-type"].startswith("text/html; charset=utf-8")
    for user, status in [(uuid4(), 404), (run.owner_user_id, 409)]:
        run.status = "running"
        with pytest.raises(HTTPException) as exc:
            runs.export_run(run.id, SimpleNamespace(user_id=user), db)
        assert exc.value.status_code == status


def test_http_rejects_lost_session():
    class ExpiredAuth:
        def rate_limit(self, key, limit):
            return None

        def authenticate(self, token):
            return None

    app = create_app(auth=ExpiredAuth(), auth_settings=AuthSettings())
    with TestClient(app, base_url="https://example.test") as client:
        response = client.get(f"/api/v1/runs/{uuid4()}/export")
    assert response.status_code == 401
