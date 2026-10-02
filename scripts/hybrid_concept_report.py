"""Generate measured HYBRID-001 comparison artifacts from a completed checkpoint."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.services.technical_concepts import normalize_concept_name
from app.storage.repositories import make_engine

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs/analysis/GRAPH_CORPUS_AUDIT"
OUT = ROOT / "docs/validation/HYBRID-001"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(name: str, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def components(doc_ids: list[str], concept_docs: dict[str, set[str]]) -> tuple[int, int, int]:
    parent = {doc: doc for doc in doc_ids}

    def find(item: str) -> str:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    pairs: set[tuple[str, str]] = set()
    for docs in concept_docs.values():
        ordered = sorted(docs)
        for index, left in enumerate(ordered):
            for right in ordered[index + 1 :]:
                pairs.add((left, right))
                a, b = find(left), find(right)
                if a != b:
                    parent[b] = a
    sizes = Counter(find(doc) for doc in doc_ids)
    return len(sizes), max(sizes.values(), default=0), len(pairs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", default="data/checkpoints/hybrid-001-full-v1.3.json")
    args = parser.parse_args()
    checkpoint = json.loads(Path(args.checkpoint).read_text(encoding="utf-8"))
    import os

    engine = make_engine(os.environ["DATABASE_URL"])
    with engine.connect() as connection:
        run_times = connection.execute(
            text("SELECT started_at, completed_at FROM semantic_concept_runs WHERE id=:run"),
            {"run": checkpoint["run_id"]},
        ).one()
    engine.dispose()
    total_runtime = (
        (run_times.completed_at - run_times.started_at).total_seconds()
        if run_times.completed_at and run_times.started_at
        else None
    )
    snapshot_data = json.loads(
        (ROOT / "data/checkpoints/graph002-live-20261002.snapshot.json").read_text(encoding="utf-8")
    )["snapshot"]
    ordered_ids = [row["document_id"] for row in snapshot_data["documents"]]
    code_by_id = {doc: f"D{i + 1:03d}" for i, doc in enumerate(ordered_ids)}
    corpus_export = json.loads((AUDIT / "corpus_export.json").read_text(encoding="utf-8"))
    title_by_id = {row["id"]: row["title"] for row in corpus_export["documents"]}
    mentions = checkpoint["mentions"]
    concept_meta: dict[str, dict[str, str]] = {}
    concept_docs: dict[str, set[str]] = defaultdict(set)
    doc_concepts: dict[str, set[str]] = defaultdict(set)
    mention_count: Counter[str] = Counter()
    doc_mention_count: Counter[str] = Counter()
    type_mentions: Counter[str] = Counter()
    for row in mentions:
        cid = row["concept_id"]
        concept_meta[cid] = {
            "concept_id": cid,
            "concept_type": row["concept_type"],
            "canonical_name": row["canonical_name"],
            "normalized_key": row["normalized_key"],
        }
        concept_docs[cid].add(row["document_id"])
        doc_concepts[row["document_id"]].add(cid)
        mention_count[cid] += 1
        doc_mention_count[row["document_id"]] += 1
        type_mentions[row["concept_type"]] += 1
    degree = {cid: len(docs) for cid, docs in concept_docs.items()}
    shared = {cid for cid, count in degree.items() if count > 1}
    singleton = set(concept_meta) - shared
    concept_rows: list[dict[str, Any]] = []
    for cid, item in concept_meta.items():
        concept_rows.append(
            {
                **item,
                "document_degree": degree[cid],
                "mention_count": mention_count[cid],
                "document_codes": "; ".join(sorted(code_by_id[d] for d in concept_docs[cid])),
            }
        )
    ranked = sorted(
        concept_rows,
        key=lambda row: (
            -row["document_degree"],
            -row["mention_count"],
            row["canonical_name"].casefold(),
        ),
    )
    write_csv("top_concepts.csv", ranked[:100])
    write_csv("shared_concepts.csv", [row for row in ranked if row["document_degree"] > 1])
    write_csv("singleton_concepts.csv", [row for row in ranked if row["document_degree"] == 1])
    high: list[dict[str, Any]] = [
        row for row in ranked if row["document_degree"] >= max(3, int(len(ordered_ids) * 0.05))
    ]
    generic = {
        "sensor",
        "device",
        "material",
        "technology",
        "application",
        "sensing",
        "fabrication",
        "response",
        "adsorption",
        "detection",
        "selectivity",
        "sensitivity",
        "performance",
    }
    for row in high:
        row["generic_name_flag"] = row["canonical_name"].casefold().strip() in generic
        row["type_quality_flag"] = (
            row["concept_type"] == "ANALYTE"
            and row["canonical_name"].casefold().strip() == "graphene"
        )
        row["semantic_collapse_review"] = (
            row["document_degree"] >= len(ordered_ids) * 0.20 or row["generic_name_flag"]
        )
    write_csv("high_degree_concepts.csv", high)
    write_csv(
        "concept_types.csv",
        [
            {
                "concept_type": kind,
                "mention_count": count,
                "unique_concepts": len(
                    {cid for cid, meta in concept_meta.items() if meta["concept_type"] == kind}
                ),
            }
            for kind, count in sorted(type_mentions.items())
        ],
    )

    zero_audit = read_csv(AUDIT / "zero_fact_audit.csv")
    zero_rows = []
    for row in zero_audit:
        ids = doc_concepts.get(row["document_id"], set())
        zero_rows.append(
            {
                "document_code": row["doc_no"],
                "document_id": row["document_id"],
                "title": row["title"],
                "hybrid_concept_count": doc_mention_count[row["document_id"]],
                "recovered": bool(ids),
                "concepts": "; ".join(sorted(concept_meta[cid]["canonical_name"] for cid in ids)),
            }
        )
    write_csv("zero_fact_recovery.csv", zero_rows)

    pairs = read_csv(AUDIT / "manual_pair_audit.csv")[:30]
    pair_rows = []
    manual_total = manual_recalled = 0
    for row in pairs:
        a, b = row["document_id_a"], row["document_id_b"]
        common = doc_concepts.get(a, set()) & doc_concepts.get(b, set())
        manual_terms = [
            term.strip() for term in row["human_visible_shared_concepts"].split(";") if term.strip()
        ]
        names_a = {
            normalize_concept_name(concept_meta[cid]["canonical_name"])
            for cid in doc_concepts.get(a, set())
        }
        names_b = {
            normalize_concept_name(concept_meta[cid]["canonical_name"])
            for cid in doc_concepts.get(b, set())
        }
        recalled = [
            term
            for term in manual_terms
            if normalize_concept_name(term) in names_a and normalize_concept_name(term) in names_b
        ]
        manual_total += len(manual_terms)
        manual_recalled += len(recalled)
        pair_rows.append(
            {
                "pair_rank": row["pair_rank"],
                "document_a": row["document_a"],
                "document_b": row["document_b"],
                "title_a": row["title_a"],
                "title_b": row["title_b"],
                "similarity": row["similarity"],
                "raw_shared_features": row["existing_shared_feature_count"],
                "raw_shared_gt_zero": int(row["existing_shared_feature_count"] or 0) > 0,
                "hybrid_shared_concepts": len(common),
                "hybrid_shared_gt_zero": bool(common),
                "shared_hybrid_concepts": "; ".join(
                    sorted(concept_meta[cid]["canonical_name"] for cid in common)
                ),
                "manual_shared_concepts": row["human_visible_shared_concepts"],
                "exact_manual_concepts_recalled": "; ".join(recalled),
            }
        )
    write_csv("nearest_pair_comparison.csv", pair_rows)

    sample = [
        {
            "document_code": code_by_id.get(row["document_id"], row["document_id"]),
            "title": title_by_id.get(row["document_id"], ""),
            "concept_type": row["concept_type"],
            "canonical_name": row["canonical_name"],
            "surface_text": row["surface_text"],
            "quote": row["quote"],
            "chunk_id": row["chunk_id"],
            "start_offset": row["start_offset"],
            "end_offset": row["end_offset"],
            "qualifiers": json.dumps(row["qualifiers"], ensure_ascii=False),
        }
        for row in mentions[:200]
    ]
    write_csv("concept_quality_sample.csv", sample)
    write_csv(
        "extraction_failures.csv",
        [
            {"document_id": row["document_id"], "stage": "extraction", "error": row["error"]}
            for row in checkpoint["failures"]
        ],
        ["document_id", "stage", "error"],
    )
    components_count, largest, connected_pairs = components(ordered_ids, concept_docs)
    zero_recovered = sum(row["recovered"] for row in zero_rows)
    pair_raw = sum(row["raw_shared_gt_zero"] for row in pair_rows)
    pair_hybrid = sum(row["hybrid_shared_gt_zero"] for row in pair_rows)
    generic_high = [row["canonical_name"] for row in high if row["generic_name_flag"]]
    metrics: dict[str, Any] = {
        "run_id": checkpoint["run_id"],
        "snapshot_hash": checkpoint["snapshot_hash"],
        "status": "complete"
        if len(checkpoint["completed"]) == 100 and not checkpoint["failures"]
        else "partial",
        "documents_attempted": len(ordered_ids),
        "documents_succeeded": len(checkpoint["completed"]),
        "documents_failed": len(checkpoint["failures"]),
        "total_concept_mentions": len(mentions),
        "unique_technical_concepts": len(concept_meta),
        "mentions_concept_edges": len(mentions),
        "shared_concepts": len(shared),
        "shared_concept_percent": round(100 * len(shared) / len(concept_meta), 2)
        if concept_meta
        else 0,
        "singleton_concepts": len(singleton),
        "singleton_percent": round(100 * len(singleton) / len(concept_meta), 2)
        if concept_meta
        else 0,
        "zero_concept_documents": sum(not doc_concepts.get(doc) for doc in ordered_ids),
        "raw_zero_fact_documents": len(zero_rows),
        "raw_zero_fact_recovered": zero_recovered,
        "raw_zero_fact_recovery_percent": round(100 * zero_recovered / len(zero_rows), 2)
        if zero_rows
        else 0,
        "nearest_pairs": len(pair_rows),
        "nearest_pairs_raw_shared_gt_zero": pair_raw,
        "nearest_pairs_hybrid_shared_gt_zero": pair_hybrid,
        "manual_concept_exact_recall": manual_recalled / manual_total if manual_total else None,
        "manual_concepts_recalled": manual_recalled,
        "manual_concepts_total": manual_total,
        "connected_document_pairs": connected_pairs,
        "connected_components": components_count,
        "largest_component_documents": largest,
        "high_degree_concepts": len(high),
        "high_degree_generic_concepts": sum(row["generic_name_flag"] for row in high),
        "high_degree_generic_concept_names": generic_high,
        "high_degree_type_quality_flags": sum(row["type_quality_flag"] for row in high),
        "semantic_collapse_flag": any(
            row["document_degree"] >= len(ordered_ids) * 0.20 for row in high
        ),
        "validation_rejects": checkpoint["validation_rejects"],
    }
    (OUT / "hybrid_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    perf = json.loads((OUT / "performance.json").read_text(encoding="utf-8"))
    latencies = checkpoint["latencies"]
    perf.update(
        {
            "run_id": checkpoint["run_id"],
            "llm_calls": checkpoint["llm_calls"],
            "median_sec_per_document": __import__("statistics").median(latencies)
            if latencies
            else None,
            "p95_sec_per_document": sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)]
            if latencies
            else None,
            "semantic_extraction_total_sec": sum(latencies),
            "total_runtime_sec": total_runtime,
            "total_runtime_hours": round(total_runtime / 3600, 3) if total_runtime else None,
        }
    )
    (OUT / "performance.json").write_text(json.dumps(perf, indent=2) + "\n", encoding="utf-8")
    verdict = (
        "D - Unsafe semantic collapse"
        if metrics["semantic_collapse_flag"]
        else "B - Hybrid promising but needs refinement"
        if pair_hybrid > pair_raw
        else "C - No meaningful gain"
    )
    comparison = f"""# HYBRID-001 measured comparison

Frozen snapshot `{checkpoint["snapshot_hash"]}`; run `{checkpoint["run_id"]}`.

| Metric | Raw GRAPH-001 | GRAPH-002 | Hybrid |
|---|---:|---:|---:|
| Nodes | 409 | 409 | {len(concept_meta)} |
| Edges / mentions | 417 | 417 | {len(mentions)} |
| Shared nodes/concepts | 6 | 6 | {len(shared)} |
| Singleton concepts | 403 | 403 | {len(singleton)} |
| Zero-fact / zero-concept documents | 11 | 11 | {metrics["zero_concept_documents"]} |
| Connected document pairs | 11 | 11 | {connected_pairs} |
| Largest component | 4 | 4 | {largest} |

Of 30 audited nearest pairs, raw shared features occur in {pair_raw}.
Hybrid shared concepts occur in {pair_hybrid}.
Exact manual concept recall is {metrics["manual_concept_exact_recall"]}
({manual_recalled}/{manual_total});
this literal string match undercounts semantically equivalent qualified wording.
Hybrid recovers {zero_recovered} of {len(zero_rows)} raw zero-fact documents.
{checkpoint["validation_rejects"]} model candidates failed strict validation.
High-degree generic concepts: {metrics["high_degree_generic_concepts"]}.
Flagged high-degree names: {", ".join(generic_high) or "none"}.
Semantic collapse flag: {metrics["semantic_collapse_flag"]}.

## Decision

**{verdict}**

Use pair-level evidence and source quotes to assess semantic quality.
"""
    (OUT / "comparison.md").write_text(comparison, encoding="utf-8")
    return 0 if not checkpoint["failures"] and len(checkpoint["completed"]) == 100 else 2


if __name__ == "__main__":
    raise SystemExit(main())
