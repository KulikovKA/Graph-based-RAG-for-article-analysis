"""Run the frozen 18-case Analyst comparison for LLM-004.

Usage: python scripts/llm004_benchmark.py MODEL_KEY REASONING_EFFORT
MODEL_KEY is gpt_oss or gpt_oss_sonnet; effort is low, medium, or high.
Each run checkpoints one safe, aggregate-only record per frozen case.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from statistics import median
from uuid import UUID, NAMESPACE_URL, uuid5

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/validation/LLM-004"
DATA = ROOT / "eval/llm003/analyst.jsonl"
PROMPT_PATH = ROOT / "prompts/analyst_v1.txt"
OLLAMA = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MODELS = {
    "gpt_oss": "gpt-oss:20b",
    "gpt_oss_sonnet": "ducquoc/gpt-oss-sonnet:latest",
}
EFFORTS = {"low", "medium", "high"}
MAX_OUTPUT = 2048
TIMEOUT = 600
TEMPERATURE = 0.0
TOP_P = 0.9
KEEP_ALIVE = 3600
CONTEXT_LENGTH = 131072


def uid(value: str) -> str:
    return str(uuid5(NAMESPACE_URL, "llm003:" + value))


class ComparableOllamaProvider:
    """Use the production Analyst/validator while pinning shared sampling."""

    def __init__(self, client: httpx.AsyncClient, **kwargs: object) -> None:
        from app.integrations.inference_http import OllamaProvider

        class _Pinned(OllamaProvider):
            observed_errors: list[str] = []

            async def _frames(self, body: dict[str, object]):  # type: ignore[no-untyped-def]
                pinned = dict(body)
                options = dict(pinned.get("options", {}))  # type: ignore[arg-type]
                options.update({"temperature": TEMPERATURE, "top_p": TOP_P,
                                "num_ctx": CONTEXT_LENGTH})
                pinned["options"] = options
                try:
                    async for frame in super()._frames(pinned):
                        yield frame
                except Exception as exc:
                    self.observed_errors.append(type(exc).__name__)
                    raise

        self.provider = _Pinned(client, **kwargs)  # type: ignore[arg-type]
        self.observed_errors: list[str] = []

    async def complete_json(self, **kwargs: object) -> object:
        try:
            return await self.provider.complete_json(**kwargs)  # type: ignore[arg-type]
        except Exception as exc:
            self.observed_errors.append(type(exc).__name__)
            raise

    def __getattr__(self, name: str) -> object:
        return getattr(self.provider, name)


def summarize(rows: list[dict[str, object]]) -> dict[str, object]:
    labels = ("full", "partial", "conflicting", "uncertain", "none")
    confusion = {label: {target: 0 for target in labels} for label in labels}
    per_label = {label: {"expected": 0, "exact": 0} for label in labels}
    for row in rows:
        gold = str(row["expected_relation"])
        predicted = str(row["actual_relation"])
        if gold in per_label:
            per_label[gold]["expected"] += 1
            per_label[gold]["exact"] += int(row["pass"] is True)
        if gold in confusion and predicted in confusion[gold]:
            confusion[gold][predicted] += 1
    for label in labels:
        count = per_label[label]["expected"]
        per_label[label]["accuracy"] = per_label[label]["exact"] / count if count else None
    latencies = [float(row["latency_ms"]) for row in rows]
    ordered = sorted(latencies)
    p95 = ordered[max(0, __import__("math").ceil(0.95 * len(ordered)) - 1)] if ordered else None
    return {
        "cases": len(rows), "exact_passes": sum(bool(r["pass"]) for r in rows),
        "exact_accuracy": (sum(bool(r["pass"]) for r in rows) / len(rows)) if rows else None,
        "schema_valid": sum(bool(r["schema_valid"]) for r in rows),
        "citation_valid": sum(bool(r["citation_valid"]) for r in rows),
        "fallbacks": sum(r["outcome"] == "safe_fallback" for r in rows),
        "unsupported_claim_violations": sum(bool(r["unsupported_claim"]) for r in rows),
        "reasoning_privacy_violations": sum(bool(r["reasoning_privacy_violation"]) for r in rows),
        "inference_errors": sum(bool(r["inference_error"]) for r in rows),
        "timeouts": sum(bool(r["timeout"]) for r in rows),
        "median_latency_ms": median(latencies) if latencies else None,
        "p95_latency_ms": p95,
        "median_generation_duration_ms": median(
            [float(r["generation_duration_ms"]) for r in rows if r["generation_duration_ms"] is not None]
        ) if any(r["generation_duration_ms"] is not None for r in rows) else None,
        "median_ttft_ms": median(
            [float(r["ttft_ms"]) for r in rows if r["ttft_ms"] is not None]
        ) if any(r["ttft_ms"] is not None for r in rows) else None,
        "median_output_tokens": median(
            [float(r["output_tokens"]) for r in rows if r["output_tokens"] is not None]
        ) if any(r["output_tokens"] is not None for r in rows) else None,
        "schema_gate_pass": len(rows) == 18 and all(bool(r["schema_valid"]) for r in rows),
        "citation_gate_pass": len(rows) == 18 and all(bool(r["citation_valid"]) for r in rows),
        "fallback_gate_pass": all(r["outcome"] != "safe_fallback" for r in rows),
        "unsupported_claim_gate_pass": all(not bool(r["unsupported_claim"]) for r in rows),
        "reasoning_privacy_gate_pass": all(not bool(r["reasoning_privacy_violation"]) for r in rows),
        "hard_gates_pass": len(rows) == 18 and all(
            bool(r["schema_valid"]) and bool(r["citation_valid"])
            and r["outcome"] != "safe_fallback" and not bool(r["unsupported_claim"])
            and not bool(r["reasoning_privacy_violation"]) for r in rows
        ),
        "per_label": per_label, "confusion_gold_to_predicted": confusion,
    }


def baseline_failure_comparison(runs: dict[str, object]) -> list[dict[str, object]]:
    baseline_path = ROOT / "docs/validation/LLM-003/raw/analyst_gpt-oss_20b_v4_low.jsonl"
    baseline = {r["case_id"]: r for r in
                (json.loads(line) for line in baseline_path.read_text(encoding="utf-8").splitlines())}
    failed = [case_id for case_id, row in baseline.items() if row.get("pass") is False]
    gold = {r["case_id"]: r["expected_relation"] for r in
            (json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines())}
    comparison: list[dict[str, object]] = []
    for case_id in failed:
        predictions: dict[str, dict[str, str | None]] = {}
        for model_key in MODELS:
            predictions[model_key] = {}
            for profile in ("low", "medium"):
                key = f"{model_key}_{profile}"
                path = OUT / "raw" / f"{key}.jsonl"
                if path.exists():
                    found = next((json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                                  if json.loads(line)["case_id"] == case_id), None)
                    predictions[model_key][profile] = found["actual_relation"] if found else None
                else:
                    predictions[model_key][profile] = None
        comparison.append({
            "case_id": case_id, "gold_label": gold[case_id],
            "llm003_low_prediction": baseline[case_id].get("actual_relation"),
            "predictions": predictions,
        })
    return comparison


async def main(model_key: str, effort: str) -> None:
    if model_key not in MODELS or effort not in EFFORTS:
        raise SystemExit(__doc__)
    from app.domain.contracts import CoverageV1
    from app.domain.inference import InferenceConfigurationError
    from app.domain.planner import FeatureV1, IdeaV1
    from app.services.analyst import Analyst
    from app.services.evidence_pack import EvidencePack, EvidencePackItem
    from app.workers.inference import GenerationGate

    model = MODELS[model_key]
    raw_path = OUT / "raw" / f"{model_key}_{effort}.jsonl"
    existing: dict[str, dict[str, object]] = {}
    if raw_path.exists():
        existing = {str(r["case_id"]): r for r in
                    (json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines() if line)}
    cases = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line]
    if len(cases) != 18:
        raise RuntimeError(f"Frozen Analyst fixture count changed: {len(cases)}")
    fixture_hash = hashlib.sha256(DATA.read_bytes()).hexdigest()
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    async with httpx.AsyncClient(base_url=OLLAMA, timeout=httpx.Timeout(TIMEOUT, connect=10)) as client:
        info_response = await client.post("/api/show", json={"model": model, "verbose": True})
        info_response.raise_for_status()
        info = info_response.json()
        caps = info.get("capabilities", [])
        thinking = info.get("thinking", {})
        supported = set(thinking.get("values", [])) if isinstance(thinking, dict) else set()
        if "thinking" not in caps or effort not in supported:
            raise InferenceConfigurationError(f"unsupported reasoning profile: {effort}")
        tags_response = await client.get("/api/tags")
        tags_response.raise_for_status()
        tags = {item["name"]: item for item in tags_response.json().get("models", [])}
        if model not in tags:
            raise RuntimeError(f"Exact model tag is not installed: {model}")
        digest = tags[model].get("digest", "").removeprefix("sha256:")
        if not digest:
            raise RuntimeError("Ollama did not report a model digest")

        provider = ComparableOllamaProvider(
            client, gate=GenerationGate(stop_grace=10), model_revisions={model: digest},
            supported_efforts={model: supported}, generation_keep_alive=KEEP_ALIVE,
        )
        analyst = Analyst(provider, model_id=model, prompt=prompt)  # type: ignore[arg-type]
        coverage = CoverageV1(sources=[], channels=[], partial=False, historical=False)
        rows = dict(existing)
        for case in cases:
            case_id = str(case["case_id"])
            if case_id in rows:
                continue
            f_id, doc_id, rev_id, chunk_id, evidence_id = [
                UUID(uid(case_id + suffix)) for suffix in ("f", "d", "r", "c", "e")
            ]
            quote = str(case["quote"])
            idea = IdeaV1(features=[FeatureV1(id=f_id, text=str(case["feature"]))],
                          language=str(case["language"]))
            item = EvidencePackItem(
                evidence_id=evidence_id, document_id=doc_id, revision_id=rev_id,
                chunk_id=chunk_id, source="synthetic", external_id=case_id,
                canonical_url="https://example.invalid/" + case_id, title="Synthetic fixture",
                section="abstract", language=str(case["language"]), span_start=0,
                span_end=len(quote), quoted_span=quote, retrieval_score=1.0, rerank_score=1.0,
            )
            pack = EvidencePack((item,), len(quote), 6000)
            started = time.perf_counter()
            provider.observed_errors.clear()
            timeout = False
            inference_error = False
            try:
                result = await analyst.analyze(
                    idea=idea, pack=pack, coverage=coverage,
                    request_id=f"llm004:{model_key}:{effort}:{case_id}",
                    timeout=TIMEOUT, max_output_tokens=MAX_OUTPUT, reasoning_effort=effort,
                )
            except Exception as exc:
                from app.domain.inference import InferenceTimeout
                timeout = isinstance(exc, (InferenceTimeout, TimeoutError, httpx.TimeoutException))
                inference_error = True
                row = {
                    "model": model, "digest": digest, "case_id": case_id,
                    "pass": False, "schema_valid": False, "citation_valid": False,
                    "actual_relation": "none", "expected_relation": case["expected_relation"],
                    "actual_relations": [], "unsupported_claim": False,
                    "outcome": "error", "attempts": 0, "reasoning_effort": effort,
                    "diagnostics": [type(exc).__name__],
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                    "ttft_ms": None, "generation_duration_ms": None, "output_tokens": None,
                    "timeout": timeout, "inference_error": inference_error,
                    "observed_error_types": [type(exc).__name__],
                    "reasoning_privacy_violation": False,
                    "expected_unresolved": bool(case["expect_unresolved"]), "actual_unresolved": True,
                }
            else:
                analysis = result.analysis
                relations = [r.relation for r in analysis.relations] if analysis else []
                actual = relations[0] if relations else "none"
                unresolved = analysis is None or str(f_id) in {str(x) for x in analysis.unresolved_feature_ids}
                valid = result.outcome == "analysis" and analysis is not None
                citation_valid = valid and all(
                    q.evidence_id == evidence_id and quote[q.start:q.end] == q.text
                    for relation in analysis.relations for q in relation.quotes
                )
                passed = valid and actual == case["expected_relation"] and unresolved == case["expect_unresolved"]
                public_text = json.dumps({"answer": result.answer.model_dump(mode="json"),
                                          "presentation": result.presentation.model_dump(mode="json")},
                                         ensure_ascii=False).lower()
                privacy = bool(re.search(r"<\s*/?think(?:ing)?\b|<\s*/?analysis\b", public_text))
                meta = result.metadata
                observed_errors = list(provider.observed_errors)
                timeout_seen = any(name in {"InferenceTimeout", "TimeoutException"}
                                   for name in observed_errors)
                row = {
                    "model": model, "digest": digest, "case_id": case_id,
                    "pass": bool(passed), "schema_valid": bool(valid),
                    "citation_valid": bool(citation_valid), "actual_relation": actual,
                    "expected_relation": case["expected_relation"], "actual_relations": relations,
                    "unsupported_claim": case["expected_relation"] == "none" and bool(relations),
                    "outcome": result.outcome, "attempts": result.attempts,
                    "reasoning_effort": effort, "diagnostics": list(result.diagnostic_codes),
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                    "ttft_ms": meta.model_ttft_ms if meta else None,
                    "generation_duration_ms": meta.output_duration_ms if meta else None,
                    "output_tokens": meta.output_tokens if meta else None,
                    "timeout": timeout_seen,
                    "inference_error": bool(observed_errors) or "INFERENCE_ERROR" in result.diagnostic_codes,
                    "observed_error_types": observed_errors,
                    "reasoning_privacy_violation": privacy,
                    "expected_unresolved": bool(case["expect_unresolved"]),
                    "actual_unresolved": unresolved,
                }
            rows[case_id] = row
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            ordered_rows = [rows[str(c["case_id"])] for c in cases if str(c["case_id"]) in rows]
            raw_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in ordered_rows),
                                 encoding="utf-8")
            print(f"{model_key}/{effort} {case_id}: {row['actual_relation']} "
                  f"({'PASS' if row['pass'] else 'FAIL'}) {row['latency_ms']} ms", flush=True)

        summary = summarize([rows[str(c["case_id"])] for c in cases if str(c["case_id"]) in rows])
        config = {
            "model_id": model, "digest": digest,
            "size_bytes": tags[model].get("size"),
            "quantization": info.get("details", {}).get("quantization_level"),
            "architecture": info.get("details", {}).get("family"),
            "parameter_size": info.get("details", {}).get("parameter_size"),
            "context_length": info.get("model_info", {}).get("gptoss.context_length"),
            "template_parameters": info.get("parameters"),
            "ollama_version": (await client.get("/api/version")).json().get("version"),
            "template_sha256": hashlib.sha256(info.get("template", "").encode()).hexdigest(),
            "reasoning_profiles_supported": sorted(supported),
            "reasoning_effort": effort, "temperature": TEMPERATURE, "top_p": TOP_P,
            "max_output_tokens": MAX_OUTPUT, "context_budget": CONTEXT_LENGTH,
            "timeout_seconds": TIMEOUT, "keep_alive_seconds": KEEP_ALIVE,
            "prompt_sha256": prompt_hash, "fixture_sha256": fixture_hash,
            "fixture_path": "eval/llm003/analyst.jsonl",
            "prompt_path": "prompts/analyst_v1.txt",
        }
        results_path = OUT / "results.json"
        results = json.loads(results_path.read_text(encoding="utf-8")) if results_path.exists() else {
            "schema_version": 1, "task": "LLM-004", "status": "in_progress",
            "gold_cases": 18, "runs": {},
        }
        results["runs"][f"{model_key}/{effort}"] = {"config": config, **summary}
        results["baseline_failed_case_comparison"] = baseline_failure_comparison(results["runs"])
        required_runs = {f"{key}/{profile}" for key in MODELS for profile in ("low", "medium")}
        high_raw = OUT / "raw" / "gpt_oss_high.jsonl"
        high_count = sum(1 for line in high_raw.read_text(encoding="utf-8").splitlines() if line) if high_raw.exists() else 0
        results["matrix_status"] = {
            "gpt_oss/low": "complete" if "gpt_oss/low" in results["runs"] else "not_run",
            "gpt_oss/medium": "complete" if "gpt_oss/medium" in results["runs"] else "not_run",
            "gpt_oss/high": f"partial_user_stopped_{high_count}_of_18" if high_count else "not_run_by_user_direction",
            "gpt_oss_sonnet/low": "complete" if "gpt_oss_sonnet/low" in results["runs"] else "not_run",
            "gpt_oss_sonnet/medium": "complete" if "gpt_oss_sonnet/medium" in results["runs"] else "not_run",
            "gpt_oss_sonnet/high": "not_run_by_user_direction",
        }
        if required_runs <= set(results["runs"]):
            results["status"] = "complete_low_medium_matrix"
        else:
            results["status"] = "in_progress"
        results_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "", sys.argv[2] if len(sys.argv) > 2 else ""))
