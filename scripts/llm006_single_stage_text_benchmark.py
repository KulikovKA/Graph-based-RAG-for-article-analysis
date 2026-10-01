"""Check ID-independent Tev1 inputs against the frozen relation labels."""

from __future__ import annotations

import asyncio
import json
import math
import os
import sys
import time
from pathlib import Path
from statistics import median
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from tev1_relation_benchmark import QUESTION  # noqa: E402

from app.services.relation_classifier import RelationClassifier  # noqa: E402

DATA = ROOT / "eval/llm003/analyst.jsonl"
OUT = ROOT / "docs/validation/LLM-006/raw/single_stage_text_only.jsonl"
MODEL = "tev1:4b"
LABELS = ("full", "partial", "conflicting", "uncertain", "none")


async def main() -> None:
    cases = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line]
    base = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    rows: list[dict[str, Any]] = []
    async with httpx.AsyncClient(base_url=base, timeout=httpx.Timeout(180, connect=10)) as client:
        checker = RelationClassifier(client, model_id=MODEL, digest="")
        for case in cases:
            payload = {
                "model": MODEL,
                "state": {
                    "feature_id": "feature",
                    "feature_text": case["feature"],
                    "feature_language": case["language"],
                    "evidence_id": "evidence",
                    "evidence_text": case["quote"],
                },
                "questions": {"relation": QUESTION},
                "keep_alive": "30m",
            }
            started = time.perf_counter()
            try:
                response = await client.post("/v1/systemone", json=payload)
                response.raise_for_status()
                body = response.json()
                prediction, probabilities, confidence = checker._validate(body)
                error = None
            except Exception as exc:
                prediction, probabilities, confidence = None, None, None
                error = type(exc).__name__
            rows.append({
                "case_id": case["case_id"], "gold": case["expected_relation"],
                "predicted": prediction, "probabilities": probabilities,
                "confidence": confidence,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "error": error,
            })
            OUT.write_text(
                "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                encoding="utf-8",
            )
            print(f"{case['case_id']}: {prediction} {rows[-1]['latency_ms']} ms", flush=True)
    confusion = {g: {p: 0 for p in LABELS} for g in LABELS}
    per_class = {g: {"cases": 0, "correct": 0} for g in LABELS}
    for row in rows:
        gold, pred = row["gold"], row["predicted"]
        per_class[gold]["cases"] += 1
        per_class[gold]["correct"] += int(gold == pred)
        if pred in LABELS:
            confusion[gold][pred] += 1
    for values in per_class.values():
        values["accuracy"] = values["correct"] / values["cases"] if values["cases"] else None
    times = sorted(row["latency_ms"] for row in rows)
    result = {
        "correct": sum(row["gold"] == row["predicted"] for row in rows),
        "cases": len(rows), "per_class": per_class,
        "confusion_gold_to_predicted": confusion,
        "median_latency_ms": median(times),
        "p95_nearest_rank_latency_ms": times[math.ceil(.95 * len(times)) - 1],
        "raw": str(OUT.relative_to(ROOT)),
    }
    (OUT.parent.parent / "single_stage_text_results.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
