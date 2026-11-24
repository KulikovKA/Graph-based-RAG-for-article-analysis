"""HTTP и PostgreSQL: экспорт использует только сохранённый снимок run."""

import os
import shutil
import subprocess
from uuid import UUID, uuid4

import pytest
from tests.contract.test_api import accepted, complete

from app.services.analysis_run import AnalysisRunService
from app.services.analyst import Analyst
from app.services.retrieval import CandidateRetrievalService
from app.storage.models import (
    AnalysisRun,
    DocumentRevision,
    EvidenceChunk,
    RunEvidence,
    SourceDocument,
)

pytest_plugins = ("tests.contract.test_api",)
pytestmark = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="no PostgreSQL test DB")


def test_export_formats_preserve_pinned_snapshot(api, tmp_path, monkeypatch):
    service, _, alice, bob = api
    _, run_id = accepted(alice)
    url = f"/api/v1/runs/{run_id}/export"
    assert alice.get(url).status_code == 409
    assert bob.get(url).status_code == 404
    complete(service, run_id)
    doc, rev, chunk, eid, new_rev = [uuid4() for _ in range(5)]
    quote = "Кириллическая цитата"
    source_url = "https://openalex.org/W1"
    with service.sessions.begin() as db:
        source = SourceDocument(
            id=doc,
            source="openalex",
            external_id="W1",
            kind="article",
            title="Исходное название",
            canonical_url=source_url,
        )
        db.add(source)
        db.flush()
        db.add(
            DocumentRevision(
                id=rev,
                document_id=doc,
                content_hash="a" * 64,
                normalized_json={},
                ingest_state="normalized",
            )
        )
        db.flush()
        db.add(
            EvidenceChunk(
                id=chunk,
                revision_id=rev,
                section="abstract",
                ordinal=0,
                text=quote,
                language="ru",
                section_start=0,
                section_end=len(quote),
                hash="b" * 64,
            )
        )
        db.flush()
        db.add(
            RunEvidence(
                run_id=UUID(run_id),
                evidence_id=eid,
                document_id=doc,
                revision_id=rev,
                chunk_id=chunk,
                span_start=0,
                span_end=len(quote),
                quoted_span=quote,
                source_url=source_url,
            )
        )
        stored = db.get(AnalysisRun, UUID(run_id))
        stored.outcome = "safe_fallback"
        stored.answer_json = {
            "summary": [
                {
                    "text": "Проверенный вывод",
                    "evidence_ids": [str(eid)],
                    "quotes": [
                        {"evidence_id": str(eid), "start": 0, "end": len(quote), "text": quote}
                    ],
                }
            ],
            "matches": [],
            "differences": [],
            "limitations": [],
            "followup_suggestions": [],
        }
        stored.evidence_snapshot_json = {
            "sources": [
                {
                    "document_id": str(doc),
                    "revision_id": str(rev),
                    "title": "Исходное название",
                    "kind": "article",
                    "url": source_url,
                    "evidence_ids": [str(eid)],
                }
            ],
            "evidence": [
                {
                    "evidence_id": str(eid),
                    "document_id": str(doc),
                    "revision_id": str(rev),
                    "chunk_id": str(chunk),
                    "span_start": 0,
                    "span_end": len(quote),
                    "quoted_span": quote,
                    "canonical_url": source_url,
                    "section": "abstract",
                    "language": "ru",
                }
            ],
            "graph_projection": {
                "schema_version": 1,
                "run_id": run_id,
                "graph_version": "snapshot-1",
                "nodes": [
                    {"id": "idea", "type": "Idea", "label": "Идея"},
                    {
                        "id": "doc",
                        "type": "ScientificWork",
                        "label": "Исходное название",
                        "document_id": str(doc),
                        "revision_id": str(rev),
                        "evidence_ids": [str(eid)],
                    },
                ],
                "edges": [
                    {
                        "id": "edge",
                        "source": "idea",
                        "target": "doc",
                        "type": "MATCHES",
                        "evidence_ids": [str(eid)],
                    }
                ],
                "next_cursor": None,
                "truncated": False,
            },
        }
    with service.sessions.begin() as db:
        source = db.get(SourceDocument, doc)
        db.add(
            DocumentRevision(
                id=new_rev,
                document_id=doc,
                content_hash="c" * 64,
                normalized_json={},
                ingest_state="normalized",
            )
        )
        source.title = "Новое название"
        source.active_revision_id = new_rev

    def forbidden(*args, **kwargs):
        raise AssertionError("Экспорт не должен вызывать retrieval или inference")

    for cls in (AnalysisRunService, CandidateRetrievalService, Analyst):
        monkeypatch.setattr(cls, "__init__", forbidden)
    html = alice.get(url)
    assert html.status_code == 200 and html.headers["content-type"].startswith("text/html")
    assert html.headers["content-disposition"] == f'attachment; filename="run-{run_id}.html"'
    assert html.headers["cache-control"] == "no-store"
    for text in ("Исходное название", str(rev), quote, "snapshot-1", "MATCHES"):
        assert text in html.text
    assert "Новое название" not in html.text and str(new_rev) not in html.text
    pdf = alice.get(url, params={"format": "pdf"})
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-")
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.headers["content-disposition"] == f'attachment; filename="run-{run_id}.pdf"'
    assert pdf.headers["cache-control"] == "no-store"
    assert b"/FontFile2" in pdf.content
    if shutil.which("pdftotext"):
        path = tmp_path / "report.pdf"
        path.write_bytes(pdf.content)
        extracted = subprocess.run(["pdftotext", str(path), "-"], check=True, capture_output=True)
        content = extracted.stdout.decode("utf-8")
        for text in ("Исходное название", str(rev), quote, "snapshot-1", "MATCHES"):
            assert text in content
        assert "Новое название" not in content and str(new_rev) not in content
    assert alice.get(url, params={"format": "invalid"}).status_code == 422
    assert bob.get(url, params={"format": "pdf"}).status_code == 404
    assert alice.get(f"/api/v1/runs/{uuid4()}/export").status_code == 404
    service.disable_account("alice@example.test")
    assert alice.get(url).status_code == 401
