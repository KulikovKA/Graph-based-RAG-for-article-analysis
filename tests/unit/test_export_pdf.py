"""Компонентные проверки локального PDF и границ сохранённого графа."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from test_export_report import fixture

from app.api.routes import runs
from app.services.export_report import render_export, render_export_pdf


def graph_for(run, db):
    item = db.rows[0][0]
    return {
        "schema_version": 1,
        "run_id": str(run.id),
        "graph_version": "снимок-v1",
        "nodes": [
            {"id": "idea", "type": "Idea", "label": "Идея <script>"},
            {
                "id": "doc",
                "type": "Patent",
                "label": "Патент",
                "document_id": str(item.document_id),
                "revision_id": str(item.revision_id),
                "evidence_ids": [str(item.evidence_id)],
            },
        ],
        "edges": [
            {
                "id": "edge",
                "source": "idea",
                "target": "doc",
                "type": "MATCHES",
                "evidence_ids": [str(item.evidence_id)],
            }
        ],
        "next_cursor": None,
        "truncated": False,
    }


def test_graph_and_pdf_use_same_snapshot(tmp_path):
    run, db = fixture()
    run.evidence_snapshot_json["graph_projection"] = graph_for(run, db)
    html = render_export(db, run)
    assert "<svg " in html and "MATCHES" in html and "снимок-v1" in html
    assert "Идея &lt;script&gt;" in html and "<script>" not in html
    pdf = render_export_pdf(db, run)
    assert pdf.startswith(b"%PDF-")
    assert b"/FontFile2" in pdf
    (tmp_path / "report.pdf").write_bytes(pdf)


@pytest.mark.parametrize(
    "mutation", ["run", "node", "evidence", "revision", "edge", "version", "null", "limit"]
)
def test_graph_corruption_fails_closed(mutation):
    run, db = fixture()
    graph = graph_for(run, db)
    run.evidence_snapshot_json["graph_projection"] = graph
    if mutation == "run":
        graph["run_id"] = str(uuid4())
    elif mutation == "node":
        graph["edges"][0]["target"] = "unknown"
    elif mutation == "evidence":
        graph["edges"][0]["evidence_ids"] = [str(uuid4())]
    elif mutation == "revision":
        graph["nodes"][1]["revision_id"] = str(uuid4())
    elif mutation == "edge":
        graph["edges"][0]["type"] = "<script>"
    elif mutation == "version":
        graph["schema_version"] = 2
    elif mutation == "null":
        run.evidence_snapshot_json["graph_projection"] = None
    else:
        graph["nodes"] = graph["nodes"] * 16
    with pytest.raises(ValueError):
        render_export(db, run)


def test_legacy_discloses_missing_graph():
    run, db = fixture()
    assert "Сохранённая проекция подграфа отсутствует" in render_export(db, run)
    assert render_export_pdf(db, run).startswith(b"%PDF-")


@pytest.mark.parametrize("edge_type", ["RELATED_TO", "SIMILAR_TO", "HAS_SHARED_CONCEPT"])
def test_semantic_edges_cannot_claim_evidence(edge_type):
    run, db = fixture()
    graph = graph_for(run, db)
    graph["edges"][0]["type"] = edge_type
    run.evidence_snapshot_json["graph_projection"] = graph
    with pytest.raises(ValueError):
        render_export(db, run)
    graph["edges"][0]["evidence_ids"] = []
    assert edge_type in render_export(db, run)


def test_structural_and_factual_edges_require_correct_provenance():
    run, db = fixture()
    graph = graph_for(run, db)
    run.evidence_snapshot_json["graph_projection"] = graph
    graph["edges"][0]["type"] = "DISCLOSES_FEATURE"
    graph["edges"][0]["evidence_ids"] = []
    with pytest.raises(ValueError):
        render_export(db, run)
    graph["edges"][0]["type"] = "HAS_FEATURE"
    with pytest.raises(ValueError):
        render_export(db, run)
    graph["nodes"][1] = {"id": "doc", "type": "IdeaFeature", "label": "Признак"}
    assert "HAS_FEATURE" in render_export(db, run)


def test_pdf_route_attachment_and_invalid_snapshot(monkeypatch):
    run, db = fixture()
    run.evidence_snapshot_json["graph_projection"] = graph_for(run, db)

    class Repo:
        def __init__(self, db):
            pass

        def get_run(self, run_id, *, owner_id):
            return run if run_id == run.id and owner_id == run.owner_user_id else None

    monkeypatch.setattr(runs, "OwnedRepository", Repo)
    from types import SimpleNamespace

    owner = SimpleNamespace(user_id=run.owner_user_id)
    response = runs.export_run(run.id, owner, db, "pdf")
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == f'attachment; filename="run-{run.id}.pdf"'
    assert response.headers["cache-control"] == "no-store"
    run.evidence_snapshot_json["graph_projection"]["run_id"] = str(uuid4())
    with pytest.raises(HTTPException) as exc:
        runs.export_run(run.id, owner, db, "pdf")
    assert exc.value.status_code == 503
