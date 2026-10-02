"""Offline audit calculations and source-anchor checks; never calls services or models."""

import csv
import hashlib
import itertools
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from app.services.technical_concepts import (  # noqa: E402
    TechnicalConceptMentionV1,
    validate_grounding,
)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_csv(name, rows, fields=None):
    with (OUT / name).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pairs(concept_documents):
    return set(
        pair
        for docs in concept_documents.values()
        for pair in itertools.combinations(sorted(docs), 2)
    )


def main():
    live = read(OUT / "live_read.json")
    cp_path = ROOT / "data/checkpoints/hybrid-001-full-v1.3.json"
    cp = read(cp_path)
    snapshot_path = ROOT / "data/checkpoints/graph002-live-20261002.snapshot.json"
    snap = read(snapshot_path)["snapshot"]
    baseline = read(ROOT / "docs/analysis/GRAPH_CORPUS_AUDIT/corpus_export.json")
    annotations = read(OUT / "source_annotations.json")["documents"]
    reviews = read(OUT / "high_degree_review.json")
    run = live["run_id"]
    assert run == cp["run_id"] == "d895217d-ebbe-4117-9066-8ae0ebcd0bdc"
    assert live["transaction_read_only"] == "on"
    documents = {d["id"]: d for d in live["documents"]}
    codes = {r["document_id"]: f"D{i + 1:03d}" for i, r in enumerate(snap["documents"])}
    states = {r["document_id"]: r for r in live["run_documents"]}
    assert len(states) == len(documents) == len(cp["completed"]) == 100
    assert set(states) == set(documents) == set(cp["completed"])
    expected_document_keys = {
        f"article-analysis-domain-v1:work:{r['document_id']}:rev:{r['revision_id']}"
        for r in snap["documents"]
    }
    assert {r["key"] for r in live["neo_documents"]} == expected_document_keys
    assert all(s["status"] == "completed" and s["error"] is None for s in states.values())
    assert all(
        states[r["document_id"]]["revision_id"]
        == r["revision_id"]
        == documents[r["document_id"]]["active_revision_id"]
        for r in snap["documents"]
    )
    revisions = {r["id"]: r for r in live["revisions"]}
    chunks = {c["id"]: c for c in live["chunks"]}
    baseline_chunks = {c["id"]: c for c in baseline["chunks"]}
    by_rev = defaultdict(list)
    for chunk in chunks.values():
        assert hashlib.sha256(chunk["text"].encode()).hexdigest() == chunk["hash"]
        assert chunk == baseline_chunks[chunk["id"]]
        sections = {
            s["name"]: s["text"]
            for s in revisions[chunk["revision_id"]]["normalized_json"]["sections"]
        }
        assert (
            sections[chunk["section"]][chunk["section_start"] : chunk["section_end"]]
            == chunk["text"]
        )
        by_rev[chunk["revision_id"]].append(chunk)
    assert len(chunks) == 136
    # Confirm there are no unchunked non-whitespace abstract characters.
    for revision in revisions.values():
        for section in revision["normalized_json"]["sections"]:
            covered = set()
            for chunk in by_rev[revision["id"]]:
                if chunk["section"] == section["name"]:
                    covered.update(range(chunk["section_start"], chunk["section_end"]))
            assert all(i in covered or char.isspace() for i, char in enumerate(section["text"]))
    assert (
        {f["id"] for f in live["facts"]}
        == {f["graph_fact_id"] for f in snap["facts"]}
        == {f["id"] for f in baseline["facts"]}
    )
    baseline_facts = {f["id"]: f for f in baseline["facts"]}
    for fact in live["facts"]:
        for field in [
            "revision_id",
            "from_key",
            "to_key",
            "edge_type",
            "chunk_id",
            "span_start",
            "span_end",
            "provenance_key",
            "logical_key_hash",
        ]:
            assert fact[field] == baseline_facts[fact["id"]][field]
    facts = Counter(f["revision_id"] for f in live["facts"])
    pg = {m["id"]: m for m in live["mentions"]}
    checkpoint = {m["mention_id"]: m for m in cp["mentions"]}
    neo = {m["mention"]["mention_id"]: m for m in live["neo_mentions"]}
    assert len(pg) == len(checkpoint) == len(neo) == 747
    assert set(pg) == set(checkpoint) == set(neo)
    concept_docs = defaultdict(set)
    doc_mentions = defaultdict(set)
    doc_concepts = defaultdict(set)
    concept_mentions = defaultdict(list)
    for mid, mention in pg.items():
        draft = {
            k: mention[k]
            for k in [
                "concept_type",
                "canonical_name",
                "surface_text",
                "quote",
                "start_offset",
                "end_offset",
                "confidence",
            ]
        }
        draft["qualifiers"] = mention["qualifiers_json"]
        validate_grounding(
            TechnicalConceptMentionV1.model_validate(draft), chunks[mention["chunk_id"]]["text"]
        )
        cp_m = checkpoint[mid]
        neo_m = neo[mid]
        for key in [
            "concept_id",
            "document_id",
            "revision_id",
            "chunk_id",
            "surface_text",
            "quote",
            "start_offset",
            "end_offset",
        ]:
            assert cp_m[key] == mention[key], (mid, key, "checkpoint")
        for key in [
            "revision_id",
            "chunk_id",
            "surface_text",
            "quote",
            "start_offset",
            "end_offset",
            "run_id",
        ]:
            assert neo_m["mention"][key] == mention[key], (mid, key, "neo4j")
        assert neo_m["concept_id"] == mention["concept_id"]
        assert (
            cp_m["qualifiers"]
            == mention["qualifiers_json"]
            == json.loads(neo_m["mention"]["qualifiers_json"])
        )
        assert (
            neo_m["document_key"]
            == cp_m["document_key"]
            == (
                f"article-analysis-domain-v1:work:{mention['document_id']}"
                f":rev:{mention['revision_id']}"
            )
        )
        assert neo_m["concept"]["concept_type"] == mention["concept_type"]
        concept_docs[mention["concept_id"]].add(mention["document_id"])
        concept_mentions[mention["concept_id"]].append(mention)
        doc_mentions[mention["document_id"]].add(mid)
        doc_concepts[mention["document_id"]].add(mention["concept_id"])
    zero = sorted((did for did in documents if not doc_mentions[did]), key=codes.get)
    assert len(zero) == 27 and {codes[d] for d in zero} == set(annotations)
    assert len(concept_docs) == 532 and sum(map(len, doc_concepts.values())) == 692
    zero_rows, diagnostics, diffs, anchors = [], [], [], []
    confusion = Counter()
    reading = []
    for did in sorted(documents, key=codes.get):
        document = documents[did]
        state = states[did]
        rev = state["revision_id"]
        raw = facts[rev]
        count = len(doc_concepts[did])
        confusion[(raw > 0, count > 0)] += 1
        texts = sorted(by_rev[rev], key=lambda c: c["ordinal"])
        row = {
            "document_code": codes[did],
            "document_id": did,
            "revision_id": rev,
            "openalex_id": document["external_id"],
            "title": document["title"],
            "chunk_count": len(texts),
            "text_length": sum(
                len(s["text"]) for s in revisions[rev]["normalized_json"]["sections"]
            ),
            "chunk_text_length": sum(len(c["text"]) for c in texts),
            "raw_graphfact_count": raw,
            "hybrid_concept_count": count,
            "persisted_mention_count": len(doc_mentions[did]),
            "run_status": state["status"],
            "attempt_count": state["attempts"],
        }
        diagnostic = {
            **row,
            "raw_candidate_count": "",
            "accepted_candidate_count": "",
            "accepted_count": len(doc_mentions[did]),
            "rejected_count": "",
            "acceptance_rate": "",
            "candidate_metrics_availability": "NOT_RECORDED",
            "cause_classification": "UNKNOWN" if not count else "HAS_PERSISTED_MENTIONS",
            "inference_status": "UNKNOWN",
            "extraction_sec_recorded": cp["latencies"][cp["completed"].index(did)],
            "information_loss": (
                "Drafts/reasons/per-document counts/provider metadata discarded; "
                "accepted_count means unique persisted mentions after deduplication."
            ),
        }
        diagnostics.append(diagnostic)
        mids = {
            mid
            for mid, n in neo.items()
            if n["document_key"] == f"article-analysis-domain-v1:work:{did}:rev:{rev}"
        }
        cids = {neo[mid]["concept_id"] for mid in mids}
        diffs.append(
            {
                "document_code": codes[did],
                "document_id": did,
                "revision_id": rev,
                "postgres_mentions": len(doc_mentions[did]),
                "neo4j_mentions": len(mids),
                "postgres_concepts": count,
                "neo4j_concepts": len(cids),
                "postgres_only_mention_ids": ";".join(sorted(doc_mentions[did] - mids)),
                "neo4j_only_mention_ids": ";".join(sorted(mids - doc_mentions[did])),
                "property_mismatches": 0,
                "status": "MATCH",
            }
        )
        if did not in zero:
            continue
        review = annotations[codes[did]]
        zero_rows.append(
            {
                **row,
                "cause_classification": "UNKNOWN",
                "source_quality_class": "A_LOW_SPECIFICITY"
                if review["assessment"] == "LOW_SPECIFICITY_SOURCE"
                else "E_CAUSE_UNKNOWN_CONCEPTS_PRESENT",
                "source_assessment": review["assessment"],
                "expected_semantic_extraction": review["expected"],
                "review_note": review["note"],
            }
        )
        reading.append(f"{codes[did]} {document['title']}")
        for chunk in texts:
            reading.append(
                f"chunk={chunk['id']} ordinal={chunk['ordinal']} chars={len(chunk['text'])}\n"
                f"{chunk['text']}\n"
            )
        for ordinal, typ, surface in review["anchors"]:
            chunk = next(c for c in texts if c["ordinal"] == ordinal)
            start = chunk["text"].find(surface)
            assert start >= 0, (codes[did], surface)
            anchors.append(
                {
                    "document_code": codes[did],
                    "document_id": did,
                    "chunk_id": chunk["id"],
                    "concept_kind": typ,
                    "exact_source_span": surface,
                    "start_offset": start,
                    "end_offset": start + len(surface),
                    "occurrence_count": chunk["text"].count(surface),
                    "annotation_status": "ASSISTANT_REVIEW_NOT_MODEL_OUTPUT",
                }
            )
    write_csv("zero_documents.csv", zero_rows)
    write_csv("document_diagnostics.csv", diagnostics)
    write_csv("postgres_neo4j_diff.csv", diffs)
    write_csv("source_concept_spans.csv", anchors)
    (OUT / "source_reading.txt").write_text("\n".join(reading), encoding="utf-8")
    write_csv(
        "raw_vs_hybrid_confusion.csv",
        [
            {
                "raw_facts": "YES" if raw else "NO",
                "hybrid_concepts": "YES" if hybrid else "NO",
                "document_count": confusion[raw, hybrid],
            }
            for raw in [True, False]
            for hybrid in [True, False]
        ],
    )
    # No fabricated historical rejection samples; header-only tables explicitly mean unavailable.
    write_csv(
        "rejection_examples.csv",
        [],
        [
            "run_id",
            "document_id",
            "chunk_id",
            "source_text",
            "surface_text",
            "quote",
            "reported_start_offset",
            "reported_end_offset",
            "expected_start_offset",
            "expected_end_offset",
            "reject_reason",
            "semantic_classification",
            "evidence_status",
        ],
    )
    write_csv(
        "unicode_offset_failures.csv",
        [],
        [
            "run_id",
            "document_id",
            "chunk_id",
            "source_text",
            "surface_text",
            "quote",
            "reported_start_offset",
            "reported_end_offset",
            "expected_start_offset",
            "expected_end_offset",
            "reject_reason",
            "evidence_status",
        ],
    )
    write_csv(
        "rejection_reasons.csv",
        [
            {
                "reason": "UNRECORDED_AGGREGATE",
                "count": cp["validation_rejects"],
                "percent_of_recorded_reject_counter": 100,
                "scope": (
                    "Cumulative final-run checkpoint; may include successful chunk prefixes "
                    "of failed document attempts."
                ),
                "availability": (
                    "No per-candidate reasons retained; not a validator reason taxonomy."
                ),
            }
        ],
    )
    ranking = sorted(
        concept_docs,
        key=lambda cid: (
            -len(concept_docs[cid]),
            concept_mentions[cid][0]["concept_type"],
            concept_mentions[cid][0]["canonical_name"].casefold(),
            cid,
        ),
    )[:30]
    high = []
    for rank, cid in enumerate(ranking, 1):
        meta = concept_mentions[cid][0]
        classification, note = reviews[meta["concept_type"] + ":" + meta["canonical_name"]]
        high.append(
            {
                "rank": rank,
                "concept_id": cid,
                "concept_type": meta["concept_type"],
                "canonical_name": meta["canonical_name"],
                "document_degree": len(concept_docs[cid]),
                "mention_count": len(concept_mentions[cid]),
                "document_codes": "; ".join(sorted(codes[d] for d in concept_docs[cid])),
                "classification": classification,
                "review_note": note,
            }
        )
    write_csv("high_degree_concepts.csv", high)
    # Explicit semantic counterexamples among accepted mentions, never mislabeled as rejects.
    findings = []
    unsupported = {"D005", "D013", "D034", "D094"}
    bad_ids = set()
    for mention in pg.values():
        code = codes[mention["document_id"]]
        if (
            code in unsupported
            and mention["concept_type"] == "ANALYTE"
            and mention["canonical_name"] in {"NO2", "NH3"}
        ):
            bad_ids.add(mention["id"])
            findings.append(
                {
                    "document_code": code,
                    "mention_id": mention["id"],
                    "concept_type": mention["concept_type"],
                    "canonical_name": mention["canonical_name"],
                    "surface_text": mention["surface_text"],
                    "quote": mention["quote"],
                    "start_offset": mention["start_offset"],
                    "end_offset": mention["end_offset"],
                    "deterministic_grounding": "PASS",
                    "semantic_assessment": "UNSUPPORTED_SPECIFIC_CANONICAL_NAME",
                    "evidence": (
                        "All stored chunks read: named analyte absent; "
                        "generic gas/gases/liquids does not entail NO2/NH3."
                    ),
                }
            )
    assert len(findings) == 8
    write_csv("accepted_semantic_findings.csv", findings)
    all_pairs = pairs(concept_docs)
    generic_old = {
        cid
        for cid, ms in concept_mentions.items()
        if ms[0]["canonical_name"]
        in {
            "sensing",
            "fabrication",
            "response",
            "adsorption",
            "detection",
            "selectivity",
            "sensitivity",
        }
    }
    generic_top30 = {r["concept_id"] for r in high if r["classification"] == "TOO_GENERIC"}
    without_bad = defaultdict(set)
    for mid, mention in pg.items():
        if mid not in bad_ids:
            without_bad[mention["concept_id"]].add(mention["document_id"])
    pair_metrics = {
        "all_connected_pairs": len(all_pairs),
        "legacy_generic_concept_nodes": len(generic_old),
        "legacy_generic_pair_union": len(pairs({c: concept_docs[c] for c in generic_old})),
        "pairs_after_removing_legacy_generic_concepts": len(
            pairs({c: v for c, v in concept_docs.items() if c not in generic_old})
        ),
        "legacy_generic_only_pairs": len(
            all_pairs - pairs({c: v for c, v in concept_docs.items() if c not in generic_old})
        ),
        "reviewed_top30_generic_nodes": len(generic_top30),
        "reviewed_top30_generic_pair_union": len(
            pairs({c: concept_docs[c] for c in generic_top30})
        ),
        "pairs_after_removing_reviewed_top30_generic_concepts": len(
            pairs({c: v for c, v in concept_docs.items() if c not in generic_top30})
        ),
        "pairs_after_removing_eight_unsupported_analyte_mentions": len(pairs(without_bad)),
        "unsupported_analyte_mentions": len(bad_ids),
        "interpretation": (
            "Offline sensitivity calculations only; no production writes; "
            "categories overlap and are not retrieval relevance judgments."
        ),
    }
    group_metrics = {}
    for label, selected in [
        ("concept_documents", [d for d in documents if d not in zero]),
        ("zero_documents", zero),
    ]:
        group_metrics[label] = {
            "documents": len(selected),
            "median_raw_candidate_count": None,
            "median_rejected_count": None,
            "median_accepted_candidate_count": None,
            "median_persisted_accepted_mentions": statistics.median(
                len(doc_mentions[d]) for d in selected
            ),
            "median_unique_concepts": statistics.median(len(doc_concepts[d]) for d in selected),
            "median_chunks": statistics.median(
                len(by_rev[states[d]["revision_id"]]) for d in selected
            ),
            "median_chunk_text_length": statistics.median(
                sum(len(c["text"]) for c in by_rev[states[d]["revision_id"]]) for d in selected
            ),
        }
    summary = {
        "run_id": run,
        "snapshot_hash": snap["snapshot_hash"],
        "audited_head": "14470be839a6aaddca2328c36cab2e4d6fe0a0fb",
        "collected_at_utc": live["collected_at_utc"],
        "documents": 100,
        "completed": 100,
        "failed": 0,
        "zero_documents": 27,
        "concept_documents": 73,
        "concepts": 532,
        "unique_document_concept_edges": 692,
        "persisted_mentions": 747,
        "neo4j_mentions": 747,
        "checkpoint_mentions": 747,
        "projection_missing_mentions": 0,
        "projection_extra_mentions": 0,
        "projection_property_mismatches": 0,
        "validated_accepted_spans": 747,
        "validated_chunk_hashes": 136,
        "raw_graphfacts": len(live["facts"]),
        "zero_document_chunks": sum(len(by_rev[states[d]["revision_id"]]) for d in zero),
        "cause_unknown_zero_documents": 27,
        "source_obvious_concept_documents": 26,
        "source_low_specificity_documents": 1,
        "manual_source_anchors": len(anchors),
        "validation_reject_counter": cp["validation_rejects"],
        "recorded_llm_calls": cp["llm_calls"],
        "document_retries": [
            {**s, "document_code": codes[s["document_id"]]}
            for s in states.values()
            if s["attempts"] > 1
        ],
        "groups": group_metrics,
        "pair_sensitivity": pair_metrics,
        "controlled_rerun": "NOT_PERFORMED",
        "historical_bottleneck": "UNKNOWN_INSUFFICIENT_ARTIFACTS",
        "verdicts": {
            "HYBRID_ARCHITECTURE": "ACCEPT_WITH_REFINEMENT",
            "CURRENT_EXTRACTOR": "REFINE",
            "CURRENT_VALIDATOR": "REFINE",
        },
    }
    (OUT / "audit_metrics.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    hashes = {
        str(p.relative_to(ROOT)): digest(p)
        for p in [
            cp_path,
            snapshot_path,
            OUT / "live_read.json",
            OUT / "runtime_read.json",
            ROOT / "scripts/hybrid_concept_backfill.py",
            ROOT / "src/app/services/technical_concepts.py",
            ROOT / "src/app/integrations/inference_http.py",
            ROOT / "migrations/versions/0007_hybrid_semantic_concepts.py",
            OUT / "source_annotations.json",
            OUT / "high_degree_review.json",
            OUT / "build_artifacts.py",
            OUT / "collect_live.py",
            OUT / "inspect_logs.py",
            OUT / "runtime_log_metadata.json",
            OUT / "log_inventory.json",
        ]
    }
    (OUT / "evidence_hashes.json").write_text(json.dumps(hashes, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
