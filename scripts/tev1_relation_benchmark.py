"""Run the isolated Tev1 relation-only benchmark against the frozen Analyst cases.

Usage: python scripts/tev1_relation_benchmark.py [--limit N]
This deliberately does not call the ordinary Ollama chat endpoint or production Analyst.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import time
from pathlib import Path
from statistics import median
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "eval/llm003/analyst.jsonl"
OUTPUT = ROOT / "docs/validation/LLM-005/raw/tev1_classifier.jsonl"
MODEL = "tev1:4b"
LABELS = ("full", "partial", "conflicting", "uncertain", "none")
MAX_STATE_BYTES = 6000
TIMEOUT_SECONDS = 180

RUBRIC = {
    "full": "Evidence directly and sufficiently supports all material aspects of the feature.",
    "partial": (
        "Evidence supports some material aspects of the feature, but not all required aspects; "
        "there is no material contradiction."
    ),
    "conflicting": "Evidence materially contradicts one or more required aspects of the feature.",
    "uncertain": (
        "Evidence is relevant, but is ambiguous or insufficient to decide whether the feature is "
        "supported or contradicted."
    ),
    "none": (
        "Evidence is unrelated to the feature and does not address its material properties; "
        "relevant evidence without a clear result is uncertain."
    ),
}
QUESTION = {
    "type": "choice",
    "instructions": "How does this evidence relate to the technical feature?",
    "criteria": RUBRIC,
}


def compact_state(case: dict[str, Any]) -> dict[str, str]:
    """Build the fixed, minimal classifier state; preserve feature and quote verbatim."""
    state = {
        "feature_id": str(case["case_id"]),
        "feature_text": str(case["feature"]),
        "feature_language": str(case["language"]),
        "evidence_id": str(case["case_id"]),
        "evidence_text": str(case["quote"]),
    }
    if (
        len(json.dumps(state, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        > MAX_STATE_BYTES
    ):
        raise ValueError("classifier state exceeds deterministic size guard")
    return state


def validate_answer(body: Any) -> tuple[str, dict[str, float], float, dict[str, Any]]:
    if (
        not isinstance(body, dict)
        or body.get("model") != MODEL
        or not isinstance(body.get("answers"), dict)
    ):
        raise ValueError("invalid_response_schema")
    answer = body["answers"].get("relation")
    if not isinstance(answer, dict) or answer.get("type") != "choice":
        raise ValueError("invalid_choice_schema")
    label = answer.get("choice")
    if label not in LABELS:
        raise ValueError("invalid_label")
    raw_probabilities = answer.get("probabilities")
    if not isinstance(raw_probabilities, dict) or set(raw_probabilities) != set(LABELS):
        raise ValueError("invalid_probabilities_schema")
    probabilities: dict[str, float] = {}
    for key in LABELS:
        value = raw_probabilities[key]
        if (
            isinstance(value, bool)
            or not isinstance(value, int | float)
            or not math.isfinite(value)
            or not 0 <= value <= 1
        ):
            raise ValueError("invalid_probability_value")
        probabilities[key] = float(value)
    if abs(sum(probabilities.values()) - 1.0) > 0.01:
        raise ValueError("probabilities_not_normalized")
    if label != max(LABELS, key=probabilities.__getitem__):
        raise ValueError("choice_probability_mismatch")
    confidence = answer.get("confidence")
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, int | float)
        or not math.isfinite(confidence)
        or not 0 <= confidence <= 1
    ):
        raise ValueError("invalid_confidence")
    usage = body.get("usage")
    if not isinstance(usage, dict):
        raise ValueError("invalid_usage_schema")
    input_tokens = usage.get("input_tokens")
    if isinstance(input_tokens, bool) or not isinstance(input_tokens, int) or input_tokens < 0:
        raise ValueError("invalid_input_token_count")
    safe_usage = usage
    return str(label), probabilities, float(confidence), safe_usage


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    confusion = {gold: {pred: 0 for pred in LABELS} for gold in LABELS}
    counts = {label: [0, 0] for label in LABELS}
    for row in rows:
        gold, predicted = row["gold"], row.get("predicted")
        if gold in counts:
            counts[gold][0] += 1
            counts[gold][1] += int(predicted == gold)
        if gold in confusion and predicted in confusion[gold]:
            confusion[gold][predicted] += 1
    per_label = {
        label: {
            "count": count,
            "correct": correct,
            "accuracy": correct / count if count else None,
        }
        for label, (count, correct) in counts.items()
    }
    good_latencies = [row["latency_ms"] for row in rows if row.get("latency_ms") is not None]
    ordered = sorted(good_latencies)
    p95 = ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)] if ordered else None
    confidence_by_outcome: dict[str, list[float]] = {"correct": [], "incorrect": []}
    for row in rows:
        if row.get("confidence") is not None:
            outcome = "correct" if row.get("predicted") == row["gold"] else "incorrect"
            confidence_by_outcome[outcome].append(float(row["confidence"]))
    confidence_summary = {
        outcome: {
            "count": len(values),
            "median": median(values) if values else None,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
        }
        for outcome, values in confidence_by_outcome.items()
    }
    return {
        "cases": len(rows),
        "correct": sum(row.get("predicted") == row["gold"] for row in rows),
        "accuracy": sum(row.get("predicted") == row["gold"] for row in rows) / len(rows)
        if rows
        else None,
        "errors": sum(row.get("error") is not None for row in rows),
        "per_class": per_label,
        "confusion_gold_to_predicted": confusion,
        "confidence_distribution_correct_vs_incorrect": confidence_summary,
        "median_latency_ms": median(good_latencies) if good_latencies else None,
        "p95_latency_ms": p95,
    }


async def main(limit: int | None) -> None:
    cases = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line]
    if len(cases) != 18:
        raise RuntimeError(f"expected 18 frozen Analyst cases, found {len(cases)}")
    if limit is not None:
        cases = cases[:limit]
    base_url = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if OUTPUT.exists():
        existing = {
            row["case_id"]: row
            for row in (
                json.loads(line) for line in OUTPUT.read_text(encoding="utf-8").splitlines() if line
            )
        }
    timeout = httpx.Timeout(TIMEOUT_SECONDS, connect=10)
    async with httpx.AsyncClient(timeout=timeout) as client:
        version_response = await client.get(f"{base_url}/api/version")
        version_response.raise_for_status()
        version = version_response.json().get("version")
        tags_response = await client.get(f"{base_url}/api/tags")
        tags_response.raise_for_status()
        tags = {model["name"]: model for model in tags_response.json().get("models", [])}
        if MODEL not in tags:
            raise RuntimeError(f"exact model tag {MODEL} is not installed")
        digest = str(tags[MODEL].get("digest", "")).removeprefix("sha256:")
        rows = dict(existing)
        for case in cases:
            case_id = str(case["case_id"])
            if case_id in rows:
                continue
            state = compact_state(case)
            payload = {
                "model": MODEL,
                "state": state,
                "questions": {"relation": QUESTION},
                "keep_alive": "30m",
            }
            request_bytes = len(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            )
            started = time.perf_counter()
            row: dict[str, Any] = {
                "case_id": case_id,
                "gold": case["expected_relation"],
                "model": MODEL,
                "digest": digest,
                "ollama_version": version,
                "input_state_bytes": len(
                    json.dumps(state, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                ),
                "request_bytes": request_bytes,
                "input_tokens": None,
                "probabilities": None,
                "confidence": None,
                "latency_ms": None,
                "truncated": False,
                "error": None,
            }
            try:
                response = await client.post(f"{base_url}/v1/systemone", json=payload)
                response.raise_for_status()
                body = response.json()
                prediction, probabilities, confidence, usage = validate_answer(body)
                row.update(
                    {
                        "predicted": prediction,
                        "probabilities": probabilities,
                        "confidence": confidence,
                        "input_tokens": usage["input_tokens"],
                    }
                )
            except (httpx.HTTPError, ValueError) as exc:
                row["predicted"] = None
                row["error"] = type(exc).__name__ if not isinstance(exc, ValueError) else str(exc)
            row["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
            rows[case_id] = row
            ordered_rows = [rows[c["case_id"]] for c in cases if c["case_id"] in rows]
            OUTPUT.write_text(
                "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in ordered_rows),
                encoding="utf-8",
            )
            print(
                json.dumps(
                    {
                        "case_id": case_id,
                        "predicted": row.get("predicted"),
                        "error": row["error"],
                        "latency_ms": row["latency_ms"],
                    },
                    ensure_ascii=False,
                )
            )
    ordered_rows = [rows[c["case_id"]] for c in cases if c["case_id"] in rows]
    print(json.dumps(summarize(ordered_rows), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit", type=int, help="run only the first N cases for endpoint smoke checks"
    )
    args = parser.parse_args()
    asyncio.run(main(args.limit))
