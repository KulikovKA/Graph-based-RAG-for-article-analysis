"""Offline CPU comparison on the frozen, synthetic EVAL-000 dev mini-set."""

from __future__ import annotations

import asyncio
import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

from huggingface_hub import snapshot_download

from app.integrations.reranker_local import LocalQwenReranker
from app.services.rerank import lexical_scores

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


async def main() -> None:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    manifest = json.loads((ROOT / "eval/fixtures/manifest.json").read_text(encoding="utf-8"))
    cases = [json.loads(line) for line in (ROOT / "eval/cases/dev_smoke.jsonl")
             .read_text(encoding="utf-8").splitlines()]
    documents = manifest["documents"]
    doc_ids = [item["external_id"] for item in documents]
    texts = [item["title"] + "\n" + item["sections"][0]["name"] + "\n"
             + item["sections"][0]["text"] for item in documents]
    # Read pinned config with the project's YAML dependency, without model downloads.
    import yaml
    model = yaml.safe_load((ROOT / "config/models.yaml").read_text(encoding="utf-8"))["reranker"]
    model_path = Path(snapshot_download(repo_id=model["model_id"], revision=model["revision"],
                                        local_files_only=True))
    reranker = LocalQwenReranker(model_id=model["model_id"], model_path=model_path,
                                 max_length=model["max_length"])
    results: dict[str, list[dict[str, Any]]] = {"bm25": [], "qwen3_0_6b": []}
    try:
        for case in cases:
            expected = set(case["expected"]["expected_source_ids"])
            if not expected:
                continue
            query = case["query"]
            bm_start = time.perf_counter()
            bm_scores = lexical_scores(query, texts)
            bm_elapsed = (time.perf_counter() - bm_start) * 1000
            qwen_start = time.perf_counter()
            qwen_scores = await reranker.score(
                model_id=model["model_id"], query=query, documents=texts,
                timeout=240, cancel=None,
            )
            qwen_elapsed = (time.perf_counter() - qwen_start) * 1000
            for name, scores, elapsed in (("bm25", bm_scores, bm_elapsed),
                                           ("qwen3_0_6b", qwen_scores, qwen_elapsed)):
                order = sorted(
                    range(len(doc_ids)), key=lambda index: (-scores[index], doc_ids[index])
                )
                first = min(
                    order.index(index) + 1
                    for index, source_id in enumerate(doc_ids)
                    if source_id in expected
                )
                results[name].append({"case_id": case["case_id"],
                    "recall_at_3": len(expected.intersection(doc_ids[i] for i in order[:3]))
                        / len(expected),
                    "reciprocal_rank": 1 / first,
                    "top_3_hit": bool(expected.intersection(doc_ids[i] for i in order[:3])),
                    "elapsed_ms": elapsed})
    finally:
        await reranker.close()
    summary = {}
    for name, rows in results.items():
        summary[name] = {
            "evaluated_cases": len(rows),
            "mrr": statistics.mean(row["reciprocal_rank"] for row in rows),
            "recall_at_3": statistics.mean(row["recall_at_3"] for row in rows),
            "top_3_hit_rate": statistics.mean(row["top_3_hit"] for row in rows),
            "median_elapsed_ms": statistics.median(row["elapsed_ms"] for row in rows),
            "cases": rows,
        }
    out = {"corpus_id": manifest["corpus_id"], "split": "dev",
           "candidate_policy": "all eight frozen synthetic fixture documents",
           "qwen_model_id": model["model_id"], "qwen_revision": model["revision"],
           "selection": ("qwen3_0_6b: higher recall_at_3 on this small dev sample; "
                        "BM25 remains explicit fallback"),
           "cpu_comparison": summary}
    destination = ROOT / "docs/validation/RANK-001/benchmark.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
