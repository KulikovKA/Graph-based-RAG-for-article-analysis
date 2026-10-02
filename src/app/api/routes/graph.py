"""Owner-scoped, bounded GraphV1 projections built only from a run snapshot."""

import base64
import binascii
import hashlib
import hmac
import json
import os
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import require_owner
from app.api.dependencies import database
from app.services.auth import Principal
from app.storage.models import AnalysisRun, GraphFact, IdeaVersion, RunEvidence

router = APIRouter(prefix="/api/v1/runs", tags=["graph"])
DB = Annotated[Session, Depends(database)]
Owner = Annotated[Principal, Depends(require_owner)]


def _key() -> bytes:
    return os.getenv("AUTH_SESSION_SECRET", "local-graph-cursor-key-change-me").encode()


def _sign(data: dict[str, Any]) -> str:
    raw = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    signature = hmac.new(_key(), raw, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(raw + b"." + signature).decode().rstrip("=")


def _read_cursor(value: str, *, owner: UUID, run: UUID, node: str, version: str) -> int:
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        body, signature = raw.rsplit(b".", 1)
        expected = hmac.new(_key(), body, hashlib.sha256).digest()
        data = json.loads(body)
        if (
            not hmac.compare_digest(signature, expected)
            or data
            != {
                "owner": str(owner),
                "run": str(run),
                "node": node,
                "version": version,
                "offset": data["offset"],
            }
            or not isinstance(data["offset"], int)
            or data["offset"] < 0
        ):
            raise ValueError
        return data["offset"]
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        raise HTTPException(400, "INVALID_CURSOR") from None


def _run(db: Session, run_id: UUID, owner: Principal) -> AnalysisRun:
    run = db.scalar(
        select(AnalysisRun).where(
            AnalysisRun.id == run_id, AnalysisRun.owner_user_id == owner.user_id
        )
    )
    if run is None:
        raise HTTPException(404, "NOT_FOUND")
    if run.status != "completed":
        raise HTTPException(409, "GRAPH_NOT_READY")
    return run


def _snapshot(db: Session, run: AnalysisRun) -> dict[str, Any]:
    sources = (run.evidence_snapshot_json or {}).get("sources", [])
    if not sources:
        sources = []
    answer = run.answer_json or {}
    matches = answer.get("matches", [])
    versions = run.config_versions_json or {}
    pipeline = versions.get("analysis_pipeline_v1", {})
    version = str(
        versions.get("graph_projection")
        or (pipeline.get("retrieval_config_hash") if isinstance(pipeline, dict) else None)
        or "graph-v1"
    )
    features: dict[str, str] = {}
    if run.idea_version_id:
        idea = db.get(IdeaVersion, run.idea_version_id)
        normalized = (idea.normalized_json if idea else {}) or {}
        items = normalized.get("features", []) if isinstance(normalized, dict) else []
        for item in items:
            if isinstance(item, dict) and item.get("id") and item.get("text"):
                features[str(item["id"])] = str(item["text"])
    nodes: list[dict[str, Any]] = [
        {
            "id": f"idea:{run.idea_version_id or run.id}",
            "type": "Idea",
            "label": "Идея анализа",
            "evidence_ids": [],
        }
    ]
    edges: list[dict[str, Any]] = []
    evidence_by_doc: dict[str, set[str]] = {}
    for item in db.scalars(select(RunEvidence).where(RunEvidence.run_id == run.id)):
        evidence_by_doc.setdefault(str(item.document_id), set()).add(str(item.evidence_id))
    source_by_id = {
        str(item.get("document_id")): item for item in sources if item.get("document_id")
    }
    used_docs = set(source_by_id)
    for doc_id, source in source_by_id.items():
        nodes.append(
            {
                "id": f"document:{doc_id}",
                "type": "Patent" if source.get("kind") == "patent" else "ScientificWork",
                "label": str(source.get("title") or "Источник")[:240],
                "document_id": doc_id,
                "revision_id": str(source.get("revision_id", "")),
                "evidence_ids": sorted(evidence_by_doc.get(doc_id, set())),
            }
        )
    for match in matches:
        fid, did = str(match.get("feature_id", "")), str(match.get("document_id", ""))
        if not fid or did not in used_docs:
            continue
        feature_id = f"feature:{fid}"
        if not any(n["id"] == feature_id for n in nodes):
            nodes.append(
                {
                    "id": feature_id,
                    "type": "IdeaFeature",
                    "label": features.get(fid, "Признак идеи")[:240],
                    "feature_id": fid,
                    "evidence_ids": [],
                }
            )
            edges.append(
                {
                    "id": f"has:{fid}",
                    "source": f"idea:{run.idea_version_id or run.id}",
                    "target": feature_id,
                    "type": "HAS_FEATURE",
                    "evidence_ids": [],
                }
            )
        cited = {
            str(eid) for claim in match.get("claims", []) for eid in claim.get("evidence_ids", [])
        }
        edges.append(
            {
                "id": f"matches:{fid}:{did}",
                "source": feature_id,
                "target": f"document:{did}",
                "type": "MATCHES",
                "evidence_ids": sorted(cited & evidence_by_doc.get(did, set())),
            }
        )
    # Bound and stabilize the initial view. Matches with no validated evidence are omitted.
    edges = [edge for edge in edges if edge["type"] != "MATCHES" or edge["evidence_ids"]]
    full_node_count, full_edge_count = len(nodes), len(edges)
    nodes = nodes[:30]
    valid = {node["id"] for node in nodes}
    edges = [edge for edge in edges if edge["source"] in valid and edge["target"] in valid][:50]
    return {
        "run_id": str(run.id),
        "graph_version": version,
        "nodes": nodes,
        "edges": edges,
        "next_cursor": None,
        "truncated": full_node_count > len(nodes) or full_edge_count > len(edges),
    }


@router.get("/{run_id}/graph")
def graph(run_id: UUID, owner: Owner, db: DB) -> dict[str, Any]:
    run = _run(db, run_id, owner)
    return _snapshot(db, run)


@router.get("/{run_id}/graph/neighbors")
def neighbors(
    run_id: UUID,
    owner: Owner,
    db: DB,
    node_id: str = Query(min_length=1, max_length=512),
    cursor: str | None = Query(default=None, max_length=2048),
    limit: int = Query(default=20, ge=1, le=20),
) -> dict[str, Any]:
    run = _run(db, run_id, owner)
    graph = _snapshot(db, run)
    if node_id not in {item["id"] for item in graph["nodes"]}:
        raise HTTPException(404, "NOT_FOUND")
    base_nodes = {item["id"]: item for item in graph["nodes"]}
    if node_id not in base_nodes:
        raise HTTPException(404, "NOT_FOUND")
    offset = (
        _read_cursor(
            cursor, owner=owner.user_id, run=run.id, node=node_id, version=graph["graph_version"]
        )
        if cursor
        else 0
    )
    adjacent = [edge for edge in graph["edges"] if node_id in {edge["source"], edge["target"]}]
    additions: dict[str, dict[str, Any]] = {}
    if base_nodes[node_id]["type"] in {"Patent", "ScientificWork"}:
        document_id = UUID(base_nodes[node_id]["document_id"])
        revision_id = UUID(base_nodes[node_id]["revision_id"])
        run_evidence = list(
            db.scalars(
                select(RunEvidence).where(
                    RunEvidence.run_id == run.id,
                    RunEvidence.document_id == document_id,
                    RunEvidence.revision_id == revision_id,
                )
            )
        )
        evidence_by_chunk: dict[UUID, list[RunEvidence]] = {}
        for evidence in run_evidence:
            evidence_by_chunk.setdefault(evidence.chunk_id, []).append(evidence)
        facts = db.scalars(
            select(GraphFact)
            .where(
                GraphFact.revision_id == revision_id,
                GraphFact.edge_type == "DISCLOSES_FEATURE",
                GraphFact.chunk_id.is_not(None),
            )
            .order_by(GraphFact.id)
        )
        grouped: dict[str, set[str]] = {}
        for fact in facts:
            for evidence in evidence_by_chunk.get(fact.chunk_id, []):
                start = fact.span_start if fact.span_start is not None else evidence.span_start
                end = fact.span_end if fact.span_end is not None else evidence.span_end
                if start < evidence.span_end and end > evidence.span_start:
                    grouped.setdefault(fact.to_key, set()).add(str(evidence.evidence_id))
        for feature_key, evidence_ids in sorted(grouped.items()):
            opaque = hashlib.sha256(feature_key.encode()).hexdigest()[:32]
            feature_node = f"technical:{opaque}"
            try:
                encoded_label = feature_key.rsplit(":", 1)[-1]
                padding = "=" * (-len(encoded_label) % 4)
                decoded_label = base64.urlsafe_b64decode(encoded_label + padding).decode("utf-8")
                label = "".join(char for char in decoded_label if char.isprintable()).strip()[:160]
            except (binascii.Error, UnicodeDecodeError, ValueError):
                label = ""
            additions[feature_node] = {
                "id": feature_node,
                "type": "TechnicalFeature",
                "label": label or "Связанный технический признак",
                "evidence_ids": sorted(evidence_ids),
            }
            adjacent.append(
                {
                    "id": f"discloses:{document_id}:{opaque}",
                    "source": node_id,
                    "target": feature_node,
                    "type": "DISCLOSES_FEATURE",
                    "evidence_ids": sorted(evidence_ids),
                }
            )
    adjacent.sort(key=lambda item: item["id"])
    # The interactive view is capped at 100 nodes/200 edges in total.
    adjacent = adjacent[:70]
    page = adjacent[offset : min(offset + limit, 70)]
    next_offset = offset + len(page)
    next_cursor = (
        _sign(
            {
                "owner": str(owner.user_id),
                "run": str(run.id),
                "node": node_id,
                "version": graph["graph_version"],
                "offset": next_offset,
            }
        )
        if next_offset < len(adjacent)
        else None
    )
    for edge in page:
        target = edge["target"] if edge["source"] == node_id else edge["source"]
        if target in additions:
            base_nodes[target] = additions[target]
    return {
        "run_id": str(run.id),
        "graph_version": graph["graph_version"],
        "nodes": list(base_nodes.values())[:100],
        "edges": page,
        "next_cursor": next_cursor,
        "truncated": next_cursor is not None,
    }
