"""Run the current Hybrid extractor against frozen zero-document chunks without DB writes."""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import os
import statistics
import subprocess
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import hybrid_concept_backfill as hybrid  # noqa: E402

from app.domain.inference import (  # noqa: E402
    InferenceCancelled,
    InferenceOutputLimit,
    InferenceProtocolError,
    InferenceTimeout,
    InferenceUnavailable,
)
from app.integrations.inference_http import OllamaProvider  # noqa: E402
from app.services.technical_concepts import (  # noqa: E402
    CONCEPT_SCHEMA_VERSION,
    concept_identity,
)
from app.storage.models import EvidenceChunk  # noqa: E402
from app.workers.inference import GenerationGate  # noqa: E402

AUDIT = ROOT / "docs/analysis/HYBRID_ZERO_AUDIT"
OUT = ROOT / "docs/validation/HYBRID_ZERO_REPLAY"
LIVE_READ = AUDIT / "live_read.json"
ZERO_CSV = AUDIT / "zero_documents.csv"
ANNOTATIONS = AUDIT / "source_annotations.json"
PHASE1 = ["D010", "D020", "D039", "D048", "D092"]
ALL_CODES = [
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


def _prompt_sha_for_text(text: str) -> str:
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


def _inputs() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    if not all(path.is_file() for path in (LIVE_READ, ZERO_CSV, ANNOTATIONS)):
        raise RuntimeError("frozen read export, document index, or annotations are missing")
    with ZERO_CSV.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    docs = {row["document_code"]: row for row in rows}
    if set(docs) != set(ALL_CODES) or len(docs) != 27:
        raise RuntimeError("zero-document index does not contain the exact historical 27")
    read = json.loads(LIVE_READ.read_text(encoding="utf-8-sig"))
    if read.get("transaction_read_only") != "on":
        raise RuntimeError("source export is not marked as read-only")
    documents = {row["id"]: row for row in read["documents"]}
    chunks: dict[str, list[dict[str, Any]]] = {}
    for row in read["chunks"]:
        chunks.setdefault(row["revision_id"], []).append(row)
    result: dict[str, dict[str, Any]] = {}
    for code, doc in docs.items():
        revision_id = doc["revision_id"]
        chunk_rows = sorted(chunks.get(revision_id, []), key=lambda row: row["ordinal"])
        if len(chunk_rows) != int(doc["chunk_count"]):
            raise RuntimeError(f"frozen chunk count mismatch: {code}")
        if doc["document_id"] not in documents:
            raise RuntimeError(f"frozen document is missing: {code}")
        for chunk in chunk_rows:
            actual = _sha(chunk["text"])
            if actual != chunk["hash"]:
                raise RuntimeError(f"frozen chunk hash mismatch: {code}/{chunk['id']}")
        result[code] = {"index": doc, "chunks": chunk_rows}
    annotation_data = json.loads(ANNOTATIONS.read_text(encoding="utf-8"))
    annotations = annotation_data.get("documents", {})
    if set(annotations) != set(ALL_CODES):
        raise RuntimeError("source annotation document set mismatch")
    return result, annotations


def _provider() -> tuple[OllamaProvider, httpx.AsyncClient]:
    base_url = os.getenv("HYBRID_REPLAY_INFERENCE_URL", "http://127.0.0.1:11434")
    client = httpx.AsyncClient(base_url=base_url, timeout=httpx.Timeout(300, connect=10))
    provider = OllamaProvider(
        client,
        gate=GenerationGate(waiting_capacity=0),
        model_revisions={hybrid.MODEL_ID: hybrid.MODEL_DIGEST},
        supported_efforts={hybrid.MODEL_ID: set()},
    )
    return provider, client


def _status(error: BaseException) -> str:
    if isinstance(error, InferenceOutputLimit):
        return "OUTPUT_LIMIT"
    if isinstance(error, InferenceTimeout):
        return "TIMEOUT"
    if isinstance(error, InferenceCancelled | asyncio.CancelledError):
        return "CANCELLED"
    if isinstance(error, InferenceUnavailable):
        return "UNAVAILABLE"
    if isinstance(error, InferenceProtocolError):
        return "UNPARSEABLE_RESULT" if "not JSON" in str(error) else "PROTOCOL_ERROR"
    return "PROCESSING_ERROR"


def _classification(chunks: list[dict[str, Any]], retry_count: int) -> str:
    if not chunks:
        return "NO_CHUNKS"
    statuses = [chunk.get("status") for chunk in chunks]
    if any(status not in ("success", "MODEL_EMPTY") for status in statuses):
        return "INFERENCE_FAILURE"
    raw = sum(chunk.get("candidate_count") or 0 for chunk in chunks)
    accepted = sum(chunk.get("accepted_candidate_count") or 0 for chunk in chunks)
    rejected = sum(chunk.get("rejected_candidate_count") or 0 for chunk in chunks)
    if retry_count:
        return "RETRY_RECOVERED"
    if len(set(statuses)) > 1:
        return "MIXED_CHUNKS"
    if raw == 0:
        return "MODEL_EMPTY"
    if accepted == 0 and rejected:
        return "ALL_REJECTED"
    if accepted and rejected:
        return "PARTIAL_ACCEPTED"
    if accepted:
        return "ACCEPTED"
    return "INFERENCE_FAILURE"


def _assert_conservation(documents: list[dict[str, Any]]) -> None:
    for document in documents:
        for chunk in document["chunks"]:
            raw = chunk.get("candidate_count")
            accepted = chunk.get("accepted_candidate_count")
            rejected = chunk.get("rejected_candidate_count")
            if raw is not None and raw != accepted + rejected:
                raise RuntimeError("candidate count conservation failed")


def _validate_observations(
    documents: list[dict[str, Any]], expected_codes: list[str], source: dict[str, dict[str, Any]]
) -> None:
    if {document["document_code"] for document in documents} != set(expected_codes):
        raise RuntimeError("phase document set is incomplete or unexpected")
    forbidden = {"prompt", "thinking", "reasoning", "raw_response", "payload", "drafts"}
    allowed_statuses = {
        "success",
        "MODEL_EMPTY",
        "OUTPUT_LIMIT",
        "TIMEOUT",
        "CANCELLED",
        "UNAVAILABLE",
        "CONFIGURATION_ERROR",
        "PROTOCOL_ERROR",
        "UNPARSEABLE_RESULT",
        "INVALID_ENVELOPE",
        "PROCESSING_ERROR",
    }
    for document in documents:
        expected_chunks = len(source[document["document_code"]]["chunks"])
        if len(document["chunks"]) != expected_chunks:
            raise RuntimeError("diagnostic chunk count is incomplete")
        for chunk in document["chunks"]:
            attempts = chunk.get("inference_attempts", [])
            if not attempts or any(
                attempt.get("status") not in allowed_statuses for attempt in attempts
            ):
                raise RuntimeError("inference attempt status is missing or unknown")
            if chunk.get("candidate_count") is not None and (
                chunk["candidate_count"]
                != chunk["accepted_candidate_count"] + chunk["rejected_candidate_count"]
            ):
                raise RuntimeError("chunk candidate conservation invariant failed")
        encoded = json.dumps(document, ensure_ascii=False).casefold()
        if any(f'"{key}"' in encoded for key in forbidden):
            raise RuntimeError("diagnostic data contains a forbidden reasoning/payload field")


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _flatten_attempts(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for doc in documents:
        for chunk in doc["chunks"]:
            for number, attempt in enumerate(chunk.get("inference_attempts", []), 1):
                rows.append(
                    {
                        "diagnostic_run_id": doc["diagnostic_run_id"],
                        "document_code": doc["document_code"],
                        "document_id": doc["document_id"],
                        "revision_id": doc["revision_id"],
                        "outer_attempt": doc["outer_attempt"],
                        "chunk_id": chunk["chunk_id"],
                        "chunk_ordinal": chunk["chunk_ordinal"],
                        "chunk_sha256": chunk["chunk_sha256"],
                        "extractor_version": hybrid.EXTRACTOR_VERSION,
                        "schema_version": CONCEPT_SCHEMA_VERSION,
                        "prompt_version": CONCEPT_SCHEMA_VERSION,
                        "schema_sha256": _sha(
                            json.dumps(hybrid.MENTION_SCHEMA, sort_keys=True, separators=(",", ":"))
                        ),
                        "prompt_sha256": chunk.get("prompt_sha256"),
                        "inference_attempt": number,
                        "inference_status": attempt.get("status"),
                        "retry_reason": attempt.get("retry_reason"),
                        "output_token_budget": attempt.get("max_output_tokens"),
                        "finish_reason": attempt.get("finish_reason"),
                        "latency_ms": attempt.get("latency_ms"),
                        "ttft_ms": attempt.get("ttft_ms"),
                        "load_ms": attempt.get("load_ms"),
                        "output_tokens": attempt.get("output_tokens"),
                        "output_tokens_reason": attempt.get("output_tokens_reason"),
                        "raw_candidates": chunk.get("candidate_count"),
                        "accepted": chunk.get("accepted_candidate_count"),
                        "rejected": chunk.get("rejected_candidate_count"),
                        "reported_offsets_valid": chunk.get("reported_offsets_valid_count"),
                        "reanchored": chunk.get("reanchored_count"),
                        "rejected_after_reanchor": chunk.get("rejected_after_reanchor_count"),
                        "rejection_reasons": json.dumps(
                            chunk.get("rejection_reasons", {}), sort_keys=True
                        ),
                    }
                )
    return rows


async def run(phase: str) -> None:
    data, annotations = _inputs()
    provider, client = _provider()
    run_id = "hybrid-zero-replay-20261003"
    try:
        version = await client.get("/api/version", timeout=10)
        version.raise_for_status()
        tags = await client.get("/api/tags", timeout=10)
        tags.raise_for_status()
        model = next(
            (row for row in tags.json().get("models", []) if row.get("name") == hybrid.MODEL_ID),
            None,
        )
        if not model or model.get("digest") != hybrid.MODEL_DIGEST:
            raise RuntimeError("configured model is absent or digest differs; no pull attempted")
        runtime_version = version.json().get("version")
        try:
            api_context = model.get("details", {}).get("context_length")
        except AttributeError:
            api_context = None
        selected = (
            PHASE1 if phase == "smoke" else [code for code in ALL_CODES if code not in PHASE1]
        )
        context_observations: set[int] = set()
        records: list[dict[str, Any]] = []
        for code in selected:
            item = data[code]
            index = item["index"]
            doc_diag: dict[str, Any] = {
                "diagnostic_run_id": run_id,
                "document_code": code,
                "document_id": index["document_id"],
                "revision_id": index["revision_id"],
                "outer_attempt": 1,
                "chunks": [],
                "expected_chunk_count": len(item["chunks"]),
                "annotation_assessment": annotations[code]["assessment"],
                "annotation_expected": annotations[code]["expected"],
            }
            accepted_identity_keys: list[str] = []
            print(
                f"[{len(records) + 1}/{len(selected)}] {code}: {len(item['chunks'])} chunks",
                flush=True,
            )
            for row in item["chunks"]:
                chunk_diag: dict[str, Any] = {
                    "chunk_id": row["id"],
                    "chunk_ordinal": row["ordinal"],
                    "chunk_sha256": row["hash"],
                    "inference_attempts": [],
                }
                doc_diag["chunks"].append(chunk_diag)
                evidence_chunk = cast(
                    EvidenceChunk, SimpleNamespace(id=row["id"], text=row["text"])
                )
                try:
                    mentions, elapsed, rejects, calls = await hybrid._extract(
                        provider, evidence_chunk, chunk_diag
                    )
                    ps = await client.get("/api/ps", timeout=5)
                    ps.raise_for_status()
                    for loaded_model in ps.json().get("models", []):
                        if loaded_model.get("name") == hybrid.MODEL_ID and isinstance(
                            loaded_model.get("context_length"), int
                        ):
                            context_observations.add(loaded_model["context_length"])
                    chunk_diag.update(
                        elapsed_ms=elapsed * 1000,
                        calls=calls,
                        final_concepts=len(mentions),
                        outcome=chunk_diag["status"],
                    )
                    chunk_identity_keys = [
                        f"{row['id']}:{mention.start_offset}:{mention.end_offset}:"
                        f"{concept_identity(mention)[0]}:{concept_identity(mention)[1]}"
                        for mention in mentions
                    ]
                    accepted_identity_keys.extend(chunk_identity_keys)
                except (Exception, asyncio.CancelledError) as error:
                    chunk_diag.update(
                        status=_status(error),
                        outcome=_status(error),
                        elapsed_ms=sum(
                            call.get("latency_ms") or 0 for call in chunk_diag["inference_attempts"]
                        ),
                        calls=len(chunk_diag["inference_attempts"]),
                        candidate_count=None,
                        accepted_candidate_count=0,
                        rejected_candidate_count=None,
                        rejection_reasons={},
                        final_concepts=0,
                    )
                records.append(doc_diag) if row is item["chunks"][-1] else None
            final_unique = len(set(accepted_identity_keys))
            accepted = sum(
                chunk.get("accepted_candidate_count") or 0 for chunk in doc_diag["chunks"]
            )
            retries = sum(
                max(0, len(chunk["inference_attempts"]) - 1) for chunk in doc_diag["chunks"]
            )
            doc_diag.update(
                raw_candidates=(
                    sum(chunk.get("candidate_count") or 0 for chunk in doc_diag["chunks"])
                    if all(chunk.get("candidate_count") is not None for chunk in doc_diag["chunks"])
                    else None
                ),
                accepted_before_dedup=(
                    accepted
                    if all(chunk.get("candidate_count") is not None for chunk in doc_diag["chunks"])
                    else None
                ),
                rejected=(
                    sum(chunk.get("rejected_candidate_count") or 0 for chunk in doc_diag["chunks"])
                    if all(chunk.get("candidate_count") is not None for chunk in doc_diag["chunks"])
                    else None
                ),
                deduplicated=accepted - final_unique,
                final_concepts=final_unique,
                retries=retries,
                final_classification=_classification(doc_diag["chunks"], retries),
            )
        if phase == "full":
            prior = json.loads((OUT / "phase1.json").read_text(encoding="utf-8"))
            records = prior["documents"] + records
        _assert_conservation(records)
        _validate_observations(records, PHASE1 if phase == "smoke" else ALL_CODES, data)
        OUT.mkdir(parents=True, exist_ok=True)
        _write_csv(
            OUT / "chunk_attempts.csv",
            _flatten_attempts(records),
            [
                "diagnostic_run_id",
                "document_code",
                "document_id",
                "revision_id",
                "outer_attempt",
                "chunk_id",
                "chunk_ordinal",
                "chunk_sha256",
                "extractor_version",
                "schema_version",
                "prompt_version",
                "schema_sha256",
                "prompt_sha256",
                "inference_attempt",
                "inference_status",
                "retry_reason",
                "output_token_budget",
                "finish_reason",
                "latency_ms",
                "ttft_ms",
                "load_ms",
                "output_tokens",
                "output_tokens_reason",
                "raw_candidates",
                "accepted",
                "rejected",
                "reported_offsets_valid",
                "reanchored",
                "rejected_after_reanchor",
                "rejection_reasons",
            ],
        )
        all_reasons: Counter[str] = Counter()
        per_doc_reasons: Counter[tuple[str, str]] = Counter()
        latencies: list[float] = []
        model_calls = 0
        retry_count = 0
        for doc in records:
            for chunk in doc["chunks"]:
                all_reasons.update(chunk.get("rejection_reasons", {}))
                per_doc_reasons.update(
                    {
                        (doc["document_code"], key): value
                        for key, value in chunk.get("rejection_reasons", {}).items()
                    }
                )
                model_calls += len(chunk.get("inference_attempts", []))
                retry_count += max(0, len(chunk.get("inference_attempts", [])) - 1)
                latencies.extend(
                    call["latency_ms"]
                    for call in chunk.get("inference_attempts", [])
                    if isinstance(call.get("latency_ms"), int | float)
                )
        summaries: list[dict[str, Any]] = []
        for code in ALL_CODES:
            doc = next((row for row in records if row["document_code"] == code), {})
            if not doc:
                summaries.append(
                    {
                        "document_code": code,
                        "historical_cause": "UNKNOWN",
                        "final_classification": "NOT_RUN",
                    }
                )
                continue
            chunks = doc["chunks"]
            inference_statuses = sorted({chunk.get("status", "UNKNOWN") for chunk in chunks})
            dominant = ";".join(
                f"{reason}:{count}"
                for reason, count in Counter(
                    {k: v for (d, k), v in per_doc_reasons.items() if d == code}
                ).most_common(3)
            )
            summaries.append(
                {
                    "document_code": code,
                    "document_id": doc["document_id"],
                    "revision_id": doc["revision_id"],
                    "chunks": len(chunks),
                    "attempts": sum(len(chunk.get("inference_attempts", [])) for chunk in chunks),
                    "inference_status": ";".join(inference_statuses),
                    "raw_candidates": doc["raw_candidates"],
                    "accepted": doc["accepted_before_dedup"],
                    "rejected": doc["rejected"],
                    "deduplicated": doc["deduplicated"],
                    "final_concepts": doc["final_concepts"],
                    "dominant_rejection_causes": dominant,
                    "retries": doc["retries"],
                    "final_diagnostic_classification": doc["final_classification"],
                    "source_annotation": doc["annotation_assessment"],
                    "historical_cause": "UNKNOWN",
                }
            )
        _write_csv(
            OUT / "document_summary.csv",
            summaries,
            [
                "document_code",
                "document_id",
                "revision_id",
                "chunks",
                "attempts",
                "inference_status",
                "raw_candidates",
                "accepted",
                "rejected",
                "deduplicated",
                "final_concepts",
                "dominant_rejection_causes",
                "retries",
                "final_diagnostic_classification",
                "source_annotation",
                "historical_cause",
            ],
        )
        reason_rows = [
            {"scope": "ALL", "document_code": "", "reason_code": key, "count": value}
            for key, value in sorted(all_reasons.items())
        ]
        reason_rows += [
            {"scope": "DOCUMENT", "document_code": doc, "reason_code": reason, "count": value}
            for (doc, reason), value in sorted(per_doc_reasons.items())
        ]
        _write_csv(
            OUT / "rejection_reasons.csv",
            reason_rows,
            ["scope", "document_code", "reason_code", "count"],
        )
        latency_summary = {
            "count": len(latencies),
            "total_ms": sum(latencies),
            "mean_ms": statistics.mean(latencies) if latencies else None,
            "median_ms": statistics.median(latencies) if latencies else None,
            "min_ms": min(latencies) if latencies else None,
            "max_ms": max(latencies) if latencies else None,
        }
        metrics = {
            "diagnostic_run_id": run_id,
            "phase": phase,
            "documents_replayed": len(records),
            "model_calls": model_calls,
            "code_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "extractor_version": hybrid.EXTRACTOR_VERSION,
            "schema_version": CONCEPT_SCHEMA_VERSION,
            "schema_sha256": _sha(
                json.dumps(hybrid.MENTION_SCHEMA, sort_keys=True, separators=(",", ":"))
            ),
            "prompt_hashing": "SHA-256 of exact per-chunk prompt; source text is not retained",
            "model": hybrid.MODEL_ID,
            "model_digest": hybrid.MODEL_DIGEST,
            "provider_version": runtime_version,
            "temperature": 0,
            "thinking": False,
            "timeout_seconds": 300,
            "output_token_budgets": [2048, 3072],
            "retry_policy": "retry once at 3072 only after OUTPUT_LIMIT at 2048",
            "model_reported_context_length": api_context,
            "effective_context_size": (
                next(iter(context_observations)) if len(context_observations) == 1 else None
            ),
            "effective_context_observations": sorted(context_observations),
            "effective_context_reason": (
                None
                if len(context_observations) == 1
                else "loaded runtime context was not observed consistently"
            ),
            "model_empty_documents": sum(
                row.get("final_classification") == "MODEL_EMPTY" for row in records
            ),
            "all_rejected_documents": sum(
                row.get("final_classification") == "ALL_REJECTED" for row in records
            ),
            "mixed_chunk_documents": sum(
                row.get("final_classification") == "MIXED_CHUNKS" for row in records
            ),
            "inference_failure_documents": sum(
                row.get("final_classification") == "INFERENCE_FAILURE" for row in records
            ),
            "total_raw_candidates_known": sum(
                chunk.get("candidate_count") or 0 for row in records for chunk in row["chunks"]
            ),
            "total_accepted_before_dedup_known": sum(
                chunk.get("accepted_candidate_count") or 0
                for row in records
                for chunk in row["chunks"]
            ),
            "total_rejected_known": sum(
                chunk.get("rejected_candidate_count") or 0
                for row in records
                for chunk in row["chunks"]
            ),
            "total_deduplicated": sum(row["deduplicated"] for row in records),
            "rejection_reason_histogram": dict(all_reasons),
            "retry_count": retry_count,
            "latency": latency_summary,
            "token_metadata_available_calls": sum(
                call.get("output_tokens") is not None
                for doc in records
                for chunk in doc["chunks"]
                for call in chunk.get("inference_attempts", [])
            ),
            "production_stores_touched": False,
        }
        (OUT / "replay_metrics.json").write_text(
            json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
        )
        (OUT / ("phase1.json" if phase == "smoke" else "phase2.json")).write_text(
            json.dumps({"documents": records}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(metrics, indent=2))
    finally:
        await client.aclose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("smoke", "full"), default="smoke")
    args = parser.parse_args()
    asyncio.run(run(args.phase))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
