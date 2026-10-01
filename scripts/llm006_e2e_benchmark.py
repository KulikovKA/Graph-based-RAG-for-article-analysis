"""Run the selected Tev1 classifier + GPT-OSS low Analyst frozen benchmark."""

from __future__ import annotations

import asyncio
import json
import math
import os
import re
import sys
import time
from pathlib import Path
from statistics import median
from uuid import NAMESPACE_URL, UUID, uuid5

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import httpx

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "eval/llm003/analyst.jsonl"
OUT = ROOT / "docs/validation/LLM-006/raw/e2e.jsonl"
OLLAMA = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
TIMEOUT = 600


def uid(value: str) -> UUID:
    return uuid5(NAMESPACE_URL, "llm003:" + value)


async def main() -> None:
    from app.domain.contracts import CoverageV1
    from app.domain.inference import InferenceConfigurationError
    from app.domain.planner import FeatureV1, IdeaV1
    from app.integrations.inference_http import OllamaProvider
    from app.services.analyst import Analyst
    from app.services.evidence_pack import EvidencePack, EvidencePackItem
    from app.services.relation_classifier import RelationClassifier
    from app.workers.inference import GenerationGate

    cases = [json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines() if line]
    if len(cases) != 18:
        raise RuntimeError("frozen fixture must contain exactly 18 rows")
    config = json.loads((ROOT / "docs/model_inventory.json").read_text(encoding="utf-8"))
    relation_model = "tev1:4b"
    analyst_model = "gpt-oss:20b"
    async with httpx.AsyncClient(
        base_url=OLLAMA, timeout=httpx.Timeout(TIMEOUT, connect=10)
    ) as client:
        tags_response = await client.get("/api/tags")
        tags_response.raise_for_status()
        tags = {item["name"]: item for item in tags_response.json().get("models", [])}
        for name, digest in (
            (relation_model, config["models"]["relation_classifier"]["digest"]),
            (analyst_model, config["models"]["analyst"]["digest"]),
        ):
            actual = str(tags.get(name, {}).get("digest", "")).removeprefix("sha256:")
            if actual != digest:
                raise InferenceConfigurationError(f"pinned digest mismatch for {name}")
        provider = OllamaProvider(
            client,
            gate=GenerationGate(stop_grace=10),
            model_revisions={analyst_model: config["models"]["analyst"]["digest"]},
            supported_efforts={analyst_model: {"low"}},
            generation_keep_alive=3600,
        )
        classifier = RelationClassifier(
            client,
            model_id=relation_model,
            digest=config["models"]["relation_classifier"]["digest"],
        )
        analyst = Analyst(provider, model_id=analyst_model, relation_classifier=classifier)  # type: ignore[arg-type]
        coverage = CoverageV1(sources=[], channels=[], partial=False, historical=False)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        rows: list[dict[str, object]] = []
        for case in cases:
            case_id = str(case["case_id"])
            feature_id, document_id, revision_id, chunk_id, evidence_id = [
                uid(case_id + suffix) for suffix in ("f", "d", "r", "c", "e")
            ]
            quote = str(case["quote"])
            idea = IdeaV1(
                features=[FeatureV1(id=feature_id, text=str(case["feature"]))],
                language=str(case["language"]),
            )
            item = EvidencePackItem(
                evidence_id=evidence_id,
                document_id=document_id,
                revision_id=revision_id,
                chunk_id=chunk_id,
                source="synthetic",
                external_id=case_id,
                canonical_url=f"https://example.invalid/{case_id}",
                title="Synthetic fixture",
                section="abstract",
                language=str(case["language"]),
                span_start=0,
                span_end=len(quote),
                quoted_span=quote,
                retrieval_score=1.0,
                rerank_score=1.0,
            )
            pack = EvidencePack((item,), len(quote), 6000)
            started = time.perf_counter()
            try:
                result = await analyst.analyze(
                    idea=idea,
                    pack=pack,
                    coverage=coverage,
                    request_id=f"llm006:e2e:{case_id}",
                    timeout=TIMEOUT,
                    max_output_tokens=2048,
                    reasoning_effort="low",
                )
                analysis = result.analysis
                relations = [r.relation for r in analysis.relations] if analysis else []
                actual = relations[0] if relations else "none"
                unresolved = analysis is None or feature_id in (
                    {UUID(str(x)) for x in analysis.unresolved_feature_ids}
                )
                citation_valid = analysis is not None and all(
                    r.document_id == document_id
                    and q.evidence_id == evidence_id
                    and quote[q.start : q.end] == q.text
                    for r in analysis.relations
                    for q in r.quotes
                )
                public = json.dumps(
                    {
                        "answer": result.answer.model_dump(mode="json"),
                        "presentation": result.presentation.model_dump(mode="json"),
                    },
                    ensure_ascii=False,
                ).lower()
                privacy = bool(re.search(r"<\s*/?think(?:ing)?\b|<\s*/?analysis\b", public))
                row = {
                    "case_id": case_id,
                    "gold": case["expected_relation"],
                    "predicted": actual,
                    "exact": actual == case["expected_relation"],
                    "outcome": result.outcome,
                    "schema_valid": analysis is not None,
                    "citation_valid": bool(citation_valid),
                    "fallback": result.outcome == "safe_fallback",
                    "unsupported": case["expected_relation"] == "none" and bool(relations),
                    "reasoning_leak": privacy,
                    "unresolved": unresolved,
                    "diagnostics": list(result.diagnostic_codes),
                    "expected_unresolved": bool(case["expect_unresolved"]),
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                    "classifier_digest": classifier.digest,
                    "analyst_digest": config["models"]["analyst"]["digest"],
                }
            except Exception as exc:
                row = {
                    "case_id": case_id,
                    "gold": case["expected_relation"],
                    "predicted": None,
                    "exact": False,
                    "outcome": "error",
                    "schema_valid": False,
                    "citation_valid": False,
                    "fallback": False,
                    "unsupported": False,
                    "reasoning_leak": False,
                    "unresolved": True,
                    "expected_unresolved": bool(case["expect_unresolved"]),
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                    "error_type": type(exc).__name__,
                }
            rows.append(row)
            OUT.write_text(
                "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
            )
            print(
                f"{case_id}: {row['predicted']} ({row['outcome']}) {row['latency_ms']} ms",
                flush=True,
            )
        labels = ("full", "partial", "conflicting", "uncertain", "none")
        confusion = {g: {p: 0 for p in labels} for g in labels}
        for row in rows:
            if row["predicted"] in labels:
                confusion[str(row["gold"])][str(row["predicted"])] += 1
        latencies = sorted(float(r["latency_ms"]) for r in rows)
        summary = {
            "cases": len(rows),
            "semantic_exact": sum(bool(r["exact"]) for r in rows),
            "schema": sum(bool(r["schema_valid"]) for r in rows),
            "citations": sum(bool(r["citation_valid"]) for r in rows),
            "fallback": sum(bool(r["fallback"]) for r in rows),
            "unsupported": sum(bool(r["unsupported"]) for r in rows),
            "reasoning_leak": sum(bool(r["reasoning_leak"]) for r in rows),
            "unresolved_match": sum(r["unresolved"] == r["expected_unresolved"] for r in rows),
            "median_latency_ms": median(latencies),
            "p95_nearest_rank_latency_ms": latencies[math.ceil(0.95 * len(latencies)) - 1],
            "confusion_gold_to_predicted": confusion,
            "hard_gates": {
                "schema_18_of_18": all(bool(r["schema_valid"]) for r in rows),
                "citations_18_of_18": all(bool(r["citation_valid"]) for r in rows),
                "fallback_zero": all(not bool(r["fallback"]) for r in rows),
                "unsupported_zero": all(not bool(r["unsupported"]) for r in rows),
                "reasoning_leak_zero": all(not bool(r["reasoning_leak"]) for r in rows),
            },
        }
        (OUT.parent.parent / "e2e_results.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
