"""Run the frozen 18-case decomposed Tev1 relation experiment."""

from __future__ import annotations

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
OUTPUT = ROOT / "docs/validation/LLM-006/raw/decomposed_classifier.jsonl"
MODEL = "tev1:4b"
LABELS = ("full", "partial", "conflicting", "uncertain", "none")
QUESTIONS = {
    "contradiction": "Does the evidence materially contradict any required aspect of the feature?",
    "supports_all": "Does the evidence directly support all material aspects of the feature?",
    "supports_some": (
        "Does the evidence directly support at least one material aspect of the feature?"
    ),
    "relevant": "Is the evidence materially relevant to the feature?",
}


def assemble(decisions: dict[str, str]) -> str:
    """Reject logical contradictions; otherwise apply the documented precedence."""
    if set(decisions) != set(QUESTIONS) or any(v not in {"yes", "no"} for v in decisions.values()):
        raise ValueError("invalid_decision_schema")
    if decisions["contradiction"] == "yes" and (
        decisions["supports_all"] == "yes" or decisions["supports_some"] == "yes"
    ):
        raise ValueError("inconsistent_contradiction_and_support")
    if decisions["supports_all"] == "yes" and decisions["supports_some"] == "no":
        raise ValueError("inconsistent_support_implication")
    if decisions["supports_some"] == "yes" and decisions["relevant"] == "no":
        raise ValueError("inconsistent_support_and_relevance")
    if decisions["contradiction"] == "yes":
        return "conflicting"
    if decisions["supports_all"] == "yes":
        return "full"
    if decisions["supports_some"] == "yes":
        return "partial"
    if decisions["relevant"] == "yes":
        return "uncertain"
    return "none"


def state_for(case: dict[str, Any]) -> dict[str, str]:
    return {
        "feature_id": str(case["case_id"]),
        "feature_text": str(case["feature"]),
        "feature_language": str(case["language"]),
        "evidence_id": str(case["case_id"]),
        "evidence_text": str(case["quote"]),
    }


def validate(body: Any) -> tuple[str, dict[str, Any]]:
    if (
        not isinstance(body, dict)
        or body.get("model") != MODEL
        or not isinstance(body.get("answers"), dict)
    ):
        raise ValueError("invalid_response_schema")
    decisions: dict[str, str] = {}
    stats: dict[str, Any] = {}
    for name in QUESTIONS:
        answer = body["answers"].get(name)
        if (
            not isinstance(answer, dict)
            or answer.get("type") != "choice"
            or answer.get("choice") not in {"yes", "no"}
        ):
            raise ValueError(f"invalid_{name}_answer")
        probs = answer.get("probabilities")
        if not isinstance(probs, dict) or set(probs) != {"yes", "no"}:
            raise ValueError(f"invalid_{name}_probabilities")
        for value in probs.values():
            if (
                isinstance(value, bool)
                or not isinstance(value, int | float)
                or not math.isfinite(value)
                or not 0 <= value <= 1
            ):
                raise ValueError(f"malformed_{name}_probability")
        if abs(sum(probs.values()) - 1) > 0.01:
            raise ValueError(f"unnormalized_{name}_probability")
        decision = answer["choice"]
        if decision != max(("yes", "no"), key=probs.__getitem__):
            raise ValueError(f"{name}_choice_probability_mismatch")
        decisions[name] = decision
        stats[name] = {"probabilities": probs, "confidence": answer.get("confidence")}
    return assemble(decisions), {"decisions": decisions, "questions": stats}


async def main() -> None:
    cases = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line]
    if len(cases) != 18:
        raise RuntimeError(f"expected 18 frozen cases, got {len(cases)}")
    base = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    timeout = httpx.Timeout(180, connect=10)
    async with httpx.AsyncClient(timeout=timeout) as client:
        version = (await client.get(f"{base}/api/version")).json().get("version")
        tags = (await client.get(f"{base}/api/tags")).json().get("models", [])
        models = {m["name"]: m for m in tags}
        if MODEL not in models:
            raise RuntimeError(f"missing model {MODEL}")
        digest = str(models[MODEL].get("digest", "")).removeprefix("sha256:")
        for case in cases:
            payload = {
                "model": MODEL,
                "state": state_for(case),
                "questions": {
                    key: {
                        "type": "choice",
                        "instructions": question,
                        "criteria": {"yes": "Yes", "no": "No"},
                    }
                    for key, question in QUESTIONS.items()
                },
                "keep_alive": "30m",
            }
            started = time.perf_counter()
            row: dict[str, Any] = {
                "case_id": case["case_id"],
                "gold": case["expected_relation"],
                "model": MODEL,
                "digest": digest,
                "ollama_version": version,
                "calls": 1,
                "latency_ms": None,
                "predicted": None,
                "error": None,
            }
            try:
                response = await client.post(f"{base}/v1/systemone", json=payload)
                response.raise_for_status()
                body = response.json()
                predicted, details = validate(body)
                row.update(details)
                row["input_tokens"] = body.get("usage", {}).get("input_tokens")
                row["output_tokens"] = body.get("usage", {}).get("output_tokens")
                row["predicted"] = predicted
            except (httpx.HTTPError, ValueError) as exc:
                row["error"] = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
            row["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
            rows.append(row)
            OUTPUT.write_text(
                "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
            )
            print(
                json.dumps(
                    {
                        "case_id": row["case_id"],
                        "predicted": row["predicted"],
                        "error": row["error"],
                        "latency_ms": row["latency_ms"],
                    },
                    ensure_ascii=False,
                )
            )
    confusion = {g: {p: 0 for p in LABELS} for g in LABELS}
    per_class = {g: {"cases": 0, "correct": 0} for g in LABELS}
    for row in rows:
        gold, pred = row["gold"], row["predicted"]
        per_class[gold]["cases"] += 1
        per_class[gold]["correct"] += int(gold == pred)
        if pred in LABELS:
            confusion[gold][pred] += 1
    for counts in per_class.values():
        counts["accuracy"] = counts["correct"] / counts["cases"] if counts["cases"] else None
    latencies = sorted(r["latency_ms"] for r in rows)
    result = {
        "cases": len(rows),
        "correct": sum(r["gold"] == r["predicted"] for r in rows),
        "per_class": per_class,
        "confusion_gold_to_predicted": confusion,
        "median_latency_ms": median(latencies),
        "p95_nearest_rank_latency_ms": latencies[math.ceil(0.95 * len(latencies)) - 1],
        "inference_calls_total": sum(r["calls"] for r in rows),
        "malformed_or_inconsistent": sum(bool(r["error"]) for r in rows),
        "raw": str(OUTPUT.relative_to(ROOT)),
    }
    (OUTPUT.parent.parent / "decomposed_results.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
