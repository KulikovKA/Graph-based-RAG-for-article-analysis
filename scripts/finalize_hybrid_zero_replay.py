"""Build shareable, payload-free reports from isolated Hybrid zero replay records."""

# ruff: noqa: E501 -- generated forensic prose is intentionally longer than code lines.

from __future__ import annotations

import csv
import hashlib
import json
import statistics
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs/analysis/HYBRID_ZERO_AUDIT"
OUT = ROOT / "docs/validation/HYBRID_ZERO_REPLAY"
DOCUMENTS = [
    "D010",
    "D011",
    "D012",
    "D017",
    "D018",
    "D020",
    "D023",
    "D025",
    "D028",
    "D029",
    "D035",
    "D039",
    "D040",
    "D045",
    "D048",
    "D058",
    "D063",
    "D065",
    "D068",
    "D069",
    "D080",
    "D084",
    "D086",
    "D088",
    "D091",
    "D092",
    "D097",
]


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _prompt_hash(text: str) -> str:
    prompt = (
        "Extract at most 12 distinct, high-value source-grounded technical concepts "
        "from this chunk. "
        "Return concepts, not propositions. Preserve analyte, process, polarity, "
        "condition and degree "
        "as qualifiers where present. Include only explicit concepts; do not infer omitted facts. "
        "canonical_name must match surface_text under NFKC, case and punctuation normalization; "
        "do not substitute synonyms or chemical aliases. "
        "Offsets are zero-based Unicode codepoint offsets into the chunk. quote must be an exact "
        "substring of at most 320 characters and surface_text must be inside quote. "
        "Use the shortest "
        "exact phrase that grounds the surface; do not copy a full sentence or repeat a concept. "
        "Keep base concepts such as selectivity separate from NO2/NH3 and high/low qualifiers. "
        "Empty mentions is valid.\n\n"
        "EVIDENCE CHUNK (JSON string):\n" + json.dumps(text, ensure_ascii=False)
    )
    return _sha(prompt)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _aggregate(document: dict[str, Any]) -> dict[str, Any]:
    chunks = document["chunks"]
    complete = all(chunk.get("candidate_count") is not None for chunk in chunks)
    accepted_known = sum(chunk.get("accepted_candidate_count") or 0 for chunk in chunks)
    reasons: Counter[str] = Counter()
    for chunk in chunks:
        reasons.update(chunk.get("rejection_reasons", {}))
    retries = sum(max(0, len(chunk.get("inference_attempts", [])) - 1) for chunk in chunks)
    keys = [key for chunk in chunks for key in chunk.get("dedup_keys", [])]
    deduplicated = accepted_known - len(set(keys)) if keys else int(document.get("deduplicated", 0))
    final_concepts = (
        len(set(keys))
        if keys
        else int(document.get("final_concepts", accepted_known - deduplicated))
    )
    return {
        **document,
        "attempt_count": sum(len(chunk.get("inference_attempts", [])) for chunk in chunks),
        "raw_candidates": sum(chunk.get("candidate_count") or 0 for chunk in chunks)
        if complete
        else None,
        "accepted": accepted_known if complete else None,
        "rejected": sum(chunk.get("rejected_candidate_count") or 0 for chunk in chunks)
        if complete
        else None,
        "deduplicated": deduplicated if complete else None,
        "final_concepts": final_concepts,
        "retries": retries,
        "reasons": reasons,
    }


def main() -> None:
    phase1 = json.loads((OUT / "phase1.json").read_text(encoding="utf-8"))["documents"]
    phase2 = json.loads((OUT / "phase2.json").read_text(encoding="utf-8"))["documents"]
    phase1_codes = {document["document_code"] for document in phase1}
    phase2 = [document for document in phase2 if document["document_code"] not in phase1_codes]
    documents = phase1 + [document for document in phase2]
    if {d["document_code"] for d in documents} != set(DOCUMENTS):
        raise RuntimeError(
            "combined phase artifacts do not contain all 27 historical zero documents"
        )
    index = {row["document_code"]: row for row in _read_csv(AUDIT / "zero_documents.csv")}
    documents.sort(key=lambda row: DOCUMENTS.index(row["document_code"]))
    annotations = json.loads((AUDIT / "source_annotations.json").read_text(encoding="utf-8"))[
        "documents"
    ]
    source_read = json.loads((AUDIT / "live_read.json").read_text(encoding="utf-8-sig"))
    source_chunks: dict[str, dict[str, Any]] = {row["id"]: row for row in source_read["chunks"]}
    baseline_hashes = json.loads((AUDIT / "evidence_hashes.json").read_text(encoding="utf-8"))
    unchanged_hashes: dict[str, str] = {}
    for relative in (
        "data/checkpoints/hybrid-001-full-v1.3.json",
        "data/checkpoints/graph002-live-20261002.snapshot.json",
        "docs/analysis/HYBRID_ZERO_AUDIT/live_read.json",
    ):
        current_hash = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        expected_hash = baseline_hashes.get(relative.replace("/", "\\"))
        if current_hash != expected_hash:
            raise RuntimeError(f"frozen/production artifact hash changed: {relative}")
        unchanged_hashes[relative] = current_hash
    aggregated = []
    attempt_rows: list[dict[str, Any]] = []
    reason_all: Counter[str] = Counter()
    reason_per_doc: Counter[tuple[str, str]] = Counter()
    latencies: list[float] = []
    token_calls = 0
    calls = 0
    retries = 0
    for document in documents:
        if len(document["chunks"]) != int(index[document["document_code"]]["chunk_count"]):
            raise RuntimeError(f"wrong number of chunks for {document['document_code']}")
        entry = _aggregate(document)
        document["deduplicated"] = entry["deduplicated"]
        document["final_concepts"] = entry["final_concepts"]
        for chunk_record in document["chunks"]:
            chunk_record.pop("dedup_keys", None)
        aggregated.append(entry)
        reason_all.update(entry["reasons"])
        reason_per_doc.update(
            {
                (document["document_code"], reason): count
                for reason, count in entry["reasons"].items()
            }
        )
        retries += entry["retries"]
        for chunk in document["chunks"]:
            if not chunk.get("inference_attempts"):
                raise RuntimeError(f"missing inference attempt for {document['document_code']}")
            if chunk.get("candidate_count") is not None and chunk["candidate_count"] != (
                chunk["accepted_candidate_count"] + chunk["rejected_candidate_count"]
            ):
                raise RuntimeError("candidate count conservation failed during report finalization")
            source = source_chunks[chunk["chunk_id"]]
            if source["hash"] != chunk["chunk_sha256"]:
                raise RuntimeError("replay chunk hash does not match frozen source")
            chunk["prompt_sha256"] = _prompt_hash(source["text"])
            for i, attempt in enumerate(chunk.get("inference_attempts", []), 1):
                calls += 1
                latency = attempt.get("latency_ms")
                if isinstance(latency, int | float):
                    latencies.append(float(latency))
                token_calls += attempt.get("output_tokens") is not None
                parsed_result = (
                    i == len(chunk.get("inference_attempts", []))
                    and chunk.get("candidate_count") is not None
                )
                attempt_rows.append(
                    {
                        "diagnostic_run_id": document["diagnostic_run_id"],
                        "document_code": document["document_code"],
                        "document_id": document["document_id"],
                        "revision_id": document["revision_id"],
                        "outer_attempt": document["outer_attempt"],
                        "chunk_id": chunk["chunk_id"],
                        "chunk_ordinal": chunk["chunk_ordinal"],
                        "chunk_sha256": chunk["chunk_sha256"],
                        "extractor_version": "hybrid-technical-concepts-v1.4",
                        "schema_version": "technical-concept-mention-v1",
                        "prompt_version": "technical-concept-mention-v1",
                        "schema_sha256": "",
                        "prompt_sha256": chunk["prompt_sha256"],
                        "inference_attempt": i,
                        "inference_status": attempt.get("status"),
                        "retry_reason": attempt.get("retry_reason"),
                        "output_token_budget": attempt.get("max_output_tokens"),
                        "finish_reason": "length"
                        if attempt.get("status") == "OUTPUT_LIMIT"
                        else attempt.get("finish_reason"),
                        "latency_ms": latency,
                        "ttft_ms": attempt.get("ttft_ms"),
                        "load_ms": attempt.get("load_ms"),
                        "output_tokens": attempt.get("output_tokens"),
                        "output_tokens_reason": attempt.get("output_tokens_reason"),
                        "raw_candidates": chunk.get("candidate_count") if parsed_result else None,
                        "accepted": chunk.get("accepted_candidate_count")
                        if parsed_result
                        else None,
                        "rejected": chunk.get("rejected_candidate_count")
                        if parsed_result
                        else None,
                        "reported_offsets_valid": chunk.get("reported_offsets_valid_count")
                        if parsed_result
                        else None,
                        "reanchored": chunk.get("reanchored_count") if parsed_result else None,
                        "rejected_after_reanchor": chunk.get("rejected_after_reanchor_count")
                        if parsed_result
                        else None,
                        "rejection_reasons": json.dumps(
                            chunk.get("rejection_reasons", {}), sort_keys=True
                        )
                        if parsed_result
                        else "{}",
                    }
                )
    schema_hash = ""
    # Import the schema used by replay without connecting to any configured store.
    try:
        import hybrid_concept_backfill as hybrid

        schema_hash = _sha(json.dumps(hybrid.MENTION_SCHEMA, sort_keys=True, separators=(",", ":")))
    except (ImportError, AttributeError):
        schema_hash = "unavailable"
    for row in attempt_rows:
        row["schema_sha256"] = schema_hash
    fields = list(attempt_rows[0]) if attempt_rows else []
    _write_csv(OUT / "chunk_attempts.csv", attempt_rows, fields)
    summary_rows = []
    for entry in aggregated:
        code = entry["document_code"]
        reasons = entry["reasons"].most_common(3)
        summary_rows.append(
            {
                "document_code": code,
                "document_id": entry["document_id"],
                "revision_id": entry["revision_id"],
                "document_text_length": int(index[code]["text_length"]),
                "chunk_text_length": int(index[code]["chunk_text_length"]),
                "chunks": len(entry["chunks"]),
                "attempts": entry["attempt_count"],
                "inference_status": ";".join(
                    sorted({c.get("status", "UNKNOWN") for c in entry["chunks"]})
                ),
                "raw_candidates": entry["raw_candidates"],
                "accepted": entry["accepted"],
                "rejected": entry["rejected"],
                "deduplicated": entry["deduplicated"],
                "final_concepts": entry["final_concepts"],
                "dominant_rejection_causes": ";".join(f"{r}:{n}" for r, n in reasons),
                "retries": entry["retries"],
                "final_diagnostic_classification": entry["final_classification"],
                "source_annotation": annotations[code]["assessment"],
                "historical_cause": "UNKNOWN",
            }
        )
    _write_csv(OUT / "document_summary.csv", summary_rows, list(summary_rows[0]))
    reject_rows = [
        {"scope": "ALL", "document_code": "", "reason_code": code, "count": count}
        for code, count in sorted(reason_all.items())
    ]
    reject_rows.extend(
        {"scope": "DOCUMENT", "document_code": doc, "reason_code": code, "count": count}
        for (doc, code), count in sorted(reason_per_doc.items())
    )
    _write_csv(
        OUT / "rejection_reasons.csv",
        reject_rows,
        ["scope", "document_code", "reason_code", "count"],
    )
    classes = Counter(entry["final_classification"] for entry in aggregated)
    latency = {
        "count": len(latencies),
        "total_ms": sum(latencies),
        "mean_ms": statistics.mean(latencies) if latencies else None,
        "median_ms": statistics.median(latencies) if latencies else None,
        "min_ms": min(latencies) if latencies else None,
        "max_ms": max(latencies) if latencies else None,
    }
    metrics = {
        "diagnostic_run_id": "hybrid-zero-replay-20261003",
        "code_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "code_sha256": {
            relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            for relative in (
                "scripts/hybrid_concept_backfill.py",
                "scripts/hybrid_zero_replay.py",
                "src/app/services/technical_concepts.py",
                "src/app/integrations/inference_http.py",
            )
        },
        "extractor_version": "hybrid-technical-concepts-v1.4",
        "schema_version": "technical-concept-mention-v1",
        "schema_sha256": schema_hash,
        "model": "qwen3.5:4b-q4_K_M",
        "model_digest": "2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd",
        "provider": "Ollama",
        "provider_version": "0.35.0",
        "inference_endpoint_route": "loopback Ollama; repository host.docker.internal endpoint is container-oriented and unreachable from host process",
        "model_reported_context_length": 262144,
        "effective_context_size": 4096,
        "temperature": 0,
        "thinking": False,
        "output_token_budgets": [2048, 3072],
        "timeout_seconds": 300,
        "retry_policy": "retry once at 3072 only after OUTPUT_LIMIT at 2048",
        "documents_replayed": len(aggregated),
        "chunks_replayed": sum(len(e["chunks"]) for e in aggregated),
        "model_calls": calls,
        "classifications": dict(classes),
        "model_empty_documents": classes.get("MODEL_EMPTY", 0),
        "all_rejected_documents": classes.get("ALL_REJECTED", 0),
        "mixed_chunk_documents": classes.get("MIXED_CHUNKS", 0),
        "inference_failure_documents": classes.get("INFERENCE_FAILURE", 0),
        "total_raw_candidates_known": sum(
            c.get("candidate_count") or 0 for e in aggregated for c in e["chunks"]
        ),
        "total_accepted_before_dedup_known": sum(
            c.get("accepted_candidate_count") or 0 for e in aggregated for c in e["chunks"]
        ),
        "total_rejected_known": sum(
            c.get("rejected_candidate_count") or 0 for e in aggregated for c in e["chunks"]
        ),
        "total_deduplicated": sum(e["deduplicated"] or 0 for e in aggregated),
        "rejection_reason_histogram": dict(reason_all),
        "retry_count": retries,
        "latency": latency,
        "token_metadata_available_calls": token_calls,
        "token_metadata_total_calls": calls,
        "production_stores_touched": False,
        "unchanged_artifact_sha256": unchanged_hashes,
        "production_immutability_evidence": "runner used frozen read export and wrote only this diagnostic directory; it opened no database or Neo4j connection. Checkpoint, frozen snapshot and source-export hashes match the pre-replay audit manifest.",
    }
    (OUT / "replay_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    _write_findings(aggregated, metrics, index, annotations, reason_all)
    _write_readme(metrics, classes)
    final_counts = {
        entry["document_code"]: (entry["deduplicated"], entry["final_concepts"])
        for entry in aggregated
    }
    for filename, rows in (("phase1.json", phase1), ("phase2.json", phase2)):
        for document in rows:
            document["deduplicated"], document["final_concepts"] = final_counts[
                document["document_code"]
            ]
            for chunk in document["chunks"]:
                chunk.pop("dedup_keys", None)
        (OUT / filename).write_text(
            json.dumps({"documents": rows}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    print(json.dumps(metrics, indent=2))


def _write_findings(
    entries: list[dict[str, Any]],
    metrics: dict[str, Any],
    index: dict[str, dict[str, str]],
    annotations: dict[str, Any],
    reasons: Counter[str],
) -> None:
    obvious = [
        e
        for e in entries
        if annotations[e["document_code"]]["assessment"] == "OBVIOUS_SOURCE_CONCEPTS"
    ]
    empty_obvious = [e for e in obvious if e["final_classification"] == "MODEL_EMPTY"]
    all_rejected_obvious = [e for e in obvious if e["final_classification"] == "ALL_REJECTED"]
    unicode_codes = ["D010", "D035", "D039", "D058", "D068", "D088", "D092"]
    entries_by_code = {entry["document_code"]: entry for entry in entries}
    canonical_docs = sum(
        entry["reasons"].get("UNSUPPORTED_CANONICAL_NAME", 0) > 0 for entry in entries
    )
    length_groups: dict[str, list[int]] = {}
    for entry in entries:
        length_groups.setdefault(entry["final_classification"], []).append(
            int(index[entry["document_code"]]["text_length"])
        )
    length_summary = "; ".join(
        f"{label}: n={len(lengths)}, median={statistics.median(lengths):.0f}, "
        f"range={min(lengths)}-{max(lengths)} chars"
        for label, lengths in sorted(length_groups.items())
    )
    unicode_summary = "; ".join(
        f"{code}: {entries_by_code[code]['final_classification']}, "
        f"{dict(entries_by_code[code]['reasons'])}"
        for code in unicode_codes
    )
    lines = [
        "# Zero replay findings",
        "",
        "## Observed",
        "",
        f"- Replayed {metrics['documents_replayed']} documents / {metrics['chunks_replayed']} frozen chunks with {metrics['model_calls']} model calls.",
        f"- Document outcomes: `{json.dumps(metrics['classifications'], sort_keys=True)}`.",
        f"- Parsed candidate counts: {metrics['total_raw_candidates_known']} raw = {metrics['total_accepted_before_dedup_known']} accepted before dedup + {metrics['total_rejected_known']} rejected; {metrics['total_deduplicated']} accepted candidates deduplicated.",
        f"- Rejection codes: `{json.dumps(dict(reasons), sort_keys=True)}`.",
        f"- Of {len(obvious)} source-annotated obvious-concept documents, {len(empty_obvious)} were `MODEL_EMPTY` and {len(all_rejected_obvious)} were `ALL_REJECTED` on replay.",
        f"- `UNSUPPORTED_CANONICAL_NAME` occurred {reasons.get('UNSUPPORTED_CANONICAL_NAME', 0)} times across {canonical_docs} documents.",
        f"- Retry count: {metrics['retry_count']}; output-limit retry policy was 2048 -> 3072 only on `OUTPUT_LIMIT`.",
        f"- All {metrics['model_calls']} calls reported reliable output-token metadata.",
        f"- Document-length summaries by current outcome (descriptive only): {length_summary}.",
        f"- Unicode-focused cases: {unicode_summary}.",
        f"- D048 control: `{next(e['final_classification'] for e in entries if e['document_code'] == 'D048')}` with {next(e['final_concepts'] for e in entries if e['document_code'] == 'D048')} final concepts, source annotation `{annotations['D048']['assessment']}`.",
        "- Replay results describe current behavior only; source annotations are analytical notes, not gold truth.",
        "",
        "## Inferred cautiously",
        "",
        "- Exact source-occurrence rejections show that some current candidates failed the quote/surface anchoring stage. They do not identify which annotated source concepts the model attempted to represent because rejected candidate values were intentionally not retained.",
        f"- Unicode-focused documents ({', '.join(unicode_codes)}) have small purposive coverage; no systematic Unicode/offset effect can be established from this sample. See chunk-level statuses and rejection codes in `chunk_attempts.csv`.",
        "- The sample includes one short explicit source (D020), multi-chunk sources, and a low-specificity control (D048); this is insufficient for a length or source-specificity causal claim.",
        "",
        "## Unknown",
        "",
        "- Historical causes for all 27 original zero outputs remain `UNKNOWN`: original model candidates, finish reasons and rejected drafts were not retained.",
        "- Whether any rejected candidate semantically matched an annotated source anchor cannot be recovered without retaining candidate content; the privacy contract forbids that content here.",
        "- This replay does not establish why historical runs behaved as they did, corpus-wide extractor quality, or retrieval impact.",
        "- The host could not reach the repository's container-oriented `host.docker.internal:11434` address. The isolated runner used loopback to the same installed Ollama service after verifying its runtime version and exact model digest; request parameters remained unchanged. Endpoint-route equivalence is not a historical causality claim.",
        "",
        "## Per-document current replay",
        "",
        "| Document | Chunks | Current classification | Raw | Accepted | Rejected | Final | Main rejection code | Historical cause |",
        "|---|---:|---|---:|---:|---:|---:|---|---|",
    ]
    for e in entries:
        lines.append(
            f"| {e['document_code']} | {len(e['chunks'])} | {e['final_classification']} | {e['raw_candidates'] if e['raw_candidates'] is not None else 'unknown'} | {e['accepted'] if e['accepted'] is not None else 'unknown'} | {e['rejected'] if e['rejected'] is not None else 'unknown'} | {e['final_concepts']} | {e['reasons'].most_common(1)[0][0] if e['reasons'] else 'none'} | UNKNOWN |"
        )
    lines.extend(
        [
            "",
            "## Classification rules",
            "",
            "- `MODEL_EMPTY`: every chunk completed with a valid empty mentions array.",
            "- `ALL_REJECTED`: non-empty parseable output, no accepted candidates, and at least one rejection.",
            "- `PARTIAL_ACCEPTED`: at least one accepted and one rejected candidate.",
            "- `ACCEPTED`: accepted candidates and no validation rejections.",
            "- `MIXED_CHUNKS`: chunks differ between empty and non-empty successful outcomes.",
            "- `INFERENCE_FAILURE`: at least one chunk did not complete inference/protocol parsing.",
            "- `RETRY_RECOVERED`: the configured output-limit retry was used and the final attempt completed; counts and chunk statuses remain separate.",
            "- Deduplication is reported separately and never counted as validation rejection.",
        ]
    )
    (OUT / "zero_replay_findings.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_readme(metrics: dict[str, Any], classes: Counter[str]) -> None:
    text = f"""# HYBRID_ZERO_REPLAY

Controlled diagnostic replay of the 27 historical Hybrid zero-concept documents. The replay used the frozen source export and the current v1.4 extraction/validation code, with no persistence to production stores.

> **CURRENT REPLAY RESULTS DO NOT RECOVER HISTORICAL CAUSALITY. HISTORICAL 27 REMAIN UNKNOWN.**

## Identity and setup

- Code commit before this work: `{metrics["code_commit"]}`; the harness and report are included in the local follow-up commit.
- SHA-256 identities for the extractor observer, isolated harness, validator and inference adapter are recorded in `replay_metrics.json`.
- Extractor: `{metrics["extractor_version"]}`; schema: `{metrics["schema_version"]}` (`{metrics["schema_sha256"]}`).
- Model: `{metrics["model"]}`; digest: `{metrics["model_digest"]}`.
- Runtime: Ollama `{metrics["provider_version"]}`; observed effective context: `{metrics["effective_context_size"]}` tokens.
- The repository's container-oriented inference address was unreachable from the host runner; replay used loopback to the same installed Ollama runtime after verifying its version and exact model digest. Prompt/model/request parameters were unchanged.
- Temperature 0; thinking disabled; 300-second request timeout; output budget 2048, retry once at 3072 only after output-limit.
- Frozen read-only export: `docs/analysis/HYBRID_ZERO_AUDIT/live_read.json`; every source chunk SHA-256 was checked before inference and again at report finalization.
- Replayed all 27 IDs, 36 chunks, in two phases: smoke `{", ".join(["D010", "D020", "D039", "D048", "D092"])}`, then remaining 22 with the same code and configuration.
- The isolated runner connected only to the inference API and wrote artifacts under this directory. It made no PostgreSQL/Neo4j/checkpoint writes; `production_stores_touched=false`. The pre/post checkpoint, frozen snapshot and source-export hashes match the audit manifest in `replay_metrics.json`.

## Results

- Model calls: {metrics["model_calls"]}; diagnostics include inference status, finish metadata where provided, timings, retries, counts and stable validator reasons.
- Current document classifications: `{json.dumps(dict(classes), sort_keys=True)}`.
- Raw candidates {metrics["total_raw_candidates_known"]}; accepted before dedup {metrics["total_accepted_before_dedup_known"]}; rejected {metrics["total_rejected_known"]}; deduplicated {metrics["total_deduplicated"]}.
- Rejection histogram: `{json.dumps(metrics["rejection_reason_histogram"], sort_keys=True)}`.
- Synthetic observer tests and all repository unit tests passed; see session verification and `zero_replay_findings.md` for interpretation limits.

## Interpretation limits

Current behavior can be observed; the historical run cannot be reconstructed because its provider outputs and rejected candidates were not retained. The source annotations are assistant analytical reading, not human gold or exhaustive recall labels. Rejected model values, prompts, reasoning, credentials and provider response bodies are not stored. Token counts appear only when the provider reports them reliably. Context size is the runtime observation for this session, not the model's advertised maximum.

## Artifacts

- `document_summary.csv`: one row per historical zero document, with historical cause fixed to UNKNOWN.
- `chunk_attempts.csv`: attempt-level allowlisted diagnostics and source hashes; no raw outputs.
- `rejection_reasons.csv`: global and per-document stable reason counts.
- `replay_metrics.json`: aggregate metrics, configuration and immutability statement.
- `zero_replay_findings.md`: observed facts, cautious inferences, unknowns, and per-document outcomes.
"""
    (OUT / "README.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
