"""Воспроизводимый короткий CPU gate LLM-002 без сохранения текста ответов моделей."""

import argparse
import asyncio
import json
import math
import os
import re
import subprocess
import sys
import time
from collections.abc import Awaitable
from dataclasses import asdict
from pathlib import Path
from typing import Any, TypeVar, cast

import httpx
import psutil
import yaml
from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.domain.inference import (  # noqa: E402
    InferenceConfigurationError,
    InferenceProtocolError,
    JsonResult,
)
from app.integrations.inference_http import OllamaProvider  # noqa: E402
from app.integrations.reranker_local import LocalQwenReranker  # noqa: E402
from app.workers.inference import GenerationGate  # noqa: E402

T = TypeVar("T")


def _config() -> dict[str, Any]:
    return cast(dict[str, Any], yaml.safe_load(
        (ROOT / "config/models.yaml").read_text(encoding="utf-8")
    ))


def _ollama_rss() -> int:
    total = 0
    seen: set[int] = set()
    for process in psutil.process_iter(["name", "memory_info"]):
        try:
            if "ollama" in (process.info["name"] or "").lower():
                for related in [process, *process.children(recursive=True)]:
                    if related.pid not in seen:
                        total += related.memory_info().rss
                        seen.add(related.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return total


def _compose_memory_bytes() -> int | None:
    try:
        output = subprocess.check_output(
            ["docker", "stats", "--no-stream", "--format", "{{json .}}"],
            text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    total = 0
    for line in output.splitlines():
        row = json.loads(line)
        if not row.get("Name", "").startswith("article-analysis-"):
            continue
        usage = row.get("MemUsage", "").split("/", 1)[0].strip()
        match = re.fullmatch(r"([0-9.]+)(B|KiB|MiB|GiB)", usage)
        if match:
            total += int(float(match.group(1)) * {
                "B": 1, "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3,
            }[match.group(2)])
    return total


async def _measure(
    operation: Awaitable[T], *, reranker: LocalQwenReranker | None = None,
) -> tuple[T, dict[str, Any]]:
    stop = asyncio.Event()
    peak = {"ollama_rss_bytes": 0, "reranker_rss_bytes": 0,
            "host_used_bytes": 0, "swap_used_bytes": 0,
            "compose_total_bytes": 0}

    async def sample() -> None:
        next_compose_sample = 0.0
        while not stop.is_set():
            peak["ollama_rss_bytes"] = max(peak["ollama_rss_bytes"], _ollama_rss())
            if reranker is not None and reranker.pid is not None:
                try:
                    rss = psutil.Process(reranker.pid).memory_info().rss
                    peak["reranker_rss_bytes"] = max(peak["reranker_rss_bytes"], rss)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            peak["host_used_bytes"] = max(peak["host_used_bytes"], psutil.virtual_memory().used)
            peak["swap_used_bytes"] = max(peak["swap_used_bytes"], psutil.swap_memory().used)
            if time.monotonic() >= next_compose_sample:
                compose_bytes = await asyncio.to_thread(_compose_memory_bytes)
                if compose_bytes is not None:
                    peak["compose_total_bytes"] = max(peak["compose_total_bytes"],
                                                      compose_bytes)
                next_compose_sample = time.monotonic() + 5
            await asyncio.sleep(0.1)

    monitor = asyncio.create_task(sample())
    started = time.perf_counter()
    try:
        value = await operation
        return value, {"elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
                       **peak}
    finally:
        stop.set()
        await monitor


async def _unload(client: httpx.AsyncClient, model_id: str) -> None:
    response = await client.post("/api/generate", json={
        "model": model_id, "prompt": "", "keep_alive": 0, "stream": False,
    }, timeout=30)
    response.raise_for_status()


def _provider(client: httpx.AsyncClient, config: dict[str, Any], *,
              reranker: LocalQwenReranker | None = None) -> OllamaProvider:
    roles = config["generation"]
    return OllamaProvider(
        client, gate=GenerationGate(stop_grace=30),
        model_revisions={item["model_id"]: item["digest"] for item in roles.values()},
        supported_efforts={item["model_id"]: set(item["reasoning_efforts"])
                           for item in roles.values()},
        reranker=reranker, generation_keep_alive="5m", embedding_keep_alive="5m",
    )


async def _inventory(client: httpx.AsyncClient, config: dict[str, Any]) -> dict[str, Any]:
    tags = (await client.get("/api/tags")).json()["models"]
    by_id = {item["name"]: item for item in tags}
    selected = [config["generation"][role]["model_id"] for role in ("planner", "analyst")]
    selected.append(config["embedding"]["model_id"])
    found = {}
    for model_id in selected:
        item = by_id[model_id]
        if item["digest"] != next(
            spec["digest"] for spec in [*config["generation"].values(), config["embedding"]]
            if spec["model_id"] == model_id
        ):
            raise RuntimeError("local model digest differs from config")
        found[model_id] = {
            "digest": item["digest"], "bytes": item["size"],
            "quantization": item["details"]["quantization_level"],
            "architecture": item["details"]["family"],
        }
    version = subprocess.check_output(["ollama", "--version"], text=True).strip()
    return {"ollama_version": version, "models": found}


async def _embedding(provider: OllamaProvider, client: httpx.AsyncClient,
                     config: dict[str, Any]) -> dict[str, Any]:
    model_id = config["embedding"]["model_id"]
    await _unload(client, model_id)
    texts = ["патент на охлаждение литий-ионной батареи",
             "A cooling loop removes heat from a lithium-ion battery pack.",
             "A blue painting hangs in a museum."]
    vectors, cold = await _measure(provider.embed(model_id=model_id, request_id="embed-cold",
                                                   texts=texts, timeout=90))
    repeated, warm = await _measure(provider.embed(model_id=model_id, request_id="embed-warm",
                                                    texts=texts, timeout=90))
    dimensions = [len(value) for value in vectors]
    if set(dimensions) != {config["embedding"]["dimension"]}:
        raise RuntimeError("measured embedding dimension differs from config")
    def norm(vector: list[float]) -> float:
        return math.sqrt(sum(value * value for value in vector))

    def cosine(a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b, strict=True)) / (norm(a) * norm(b))
    failures = 0
    for invalid in ([], [""], ["   "]):
        try:
            await provider.embed(model_id=model_id, request_id="invalid", texts=invalid)
        except InferenceConfigurationError:
            failures += 1
    cancel = asyncio.Event()
    cancel.set()
    cancelled = False
    try:
        await provider.embed(model_id=model_id, request_id="cancel", texts=texts,
                             cancel=cancel)
    except Exception as error:
        cancelled = type(error).__name__ == "InferenceCancelled"
    timed_out = False
    try:
        await provider.embed(model_id=model_id, request_id="timeout", texts=texts,
                             timeout=0.001)
    except Exception as error:
        timed_out = type(error).__name__ == "InferenceTimeout"
    await _unload(client, model_id)
    return {
        "dimension": dimensions[0], "batch_size": len(texts),
        "stable_shape": dimensions == [len(value) for value in repeated],
        "repeat_max_abs_delta": max(abs(a - b) for first, second in zip(
            vectors, repeated, strict=True) for a, b in zip(first, second, strict=True)),
        "ru_query_en_technical_cosine": cosine(vectors[0], vectors[1]),
        "ru_query_unrelated_cosine": cosine(vectors[0], vectors[2]),
        "invalid_inputs_rejected": failures, "pre_cancel_rejected": cancelled,
        "short_deadline_timed_out": timed_out,
        "cold": cold, "warm": warm,
        "warm_texts_per_second": round(len(texts) / (warm["elapsed_ms"] / 1000), 2),
    }


async def _planner(provider: OllamaProvider, client: httpx.AsyncClient,
                   config: dict[str, Any]) -> dict[str, Any]:
    model = config["generation"]["planner"]
    await _unload(client, model["model_id"])
    schema = {"type": "object", "properties": {"intent": {"type": "string"},
              "retrieve": {"type": "boolean"}}, "required": ["intent", "retrieve"],
              "additionalProperties": False}
    prompt = ("Классифицируй технический запрос: сравнить охлаждение литий-ионного "
              "аккумулятора с патентами. Верни intent='comparison' и retrieve=true. "
              "Только JSON.")
    calls = []
    for label in ("cold", "warm"):
        result, timing = await _measure(provider.complete_json(
            model_id=model["model_id"], prompt_version="probe-v1", request_id=label,
            prompt=prompt, timeout=180, schema=schema,
            max_output_tokens=model["max_output_tokens"],
        ))
        calls.append({"phase": label, "schema_valid":
                      set(result.value) == {"intent", "retrieve"}
                      and isinstance(result.value["intent"], str)
                      and isinstance(result.value["retrieve"], bool),
                      "metadata": asdict(result.metadata), **timing})
    rejected_short_output = False
    try:
        await provider.complete_json(
            model_id=model["model_id"], prompt_version="probe-v1", request_id="truncated",
            prompt=prompt, timeout=30, schema=schema, max_output_tokens=1,
        )
    except Exception as error:
        rejected_short_output = type(error).__name__ == "InferenceProtocolError"
    repaired = await provider.complete_json(
        model_id=model["model_id"], prompt_version="probe-v1", request_id="repair",
        prompt="Повтори полный ответ строго по схеме. " + prompt, timeout=60,
        schema=schema, max_output_tokens=model["max_output_tokens"],
    )
    await _unload(client, model["model_id"])
    return {"calls": calls, "truncated_rejected": rejected_short_output,
            "single_repair_schema_valid": set(repaired.value) == {"intent", "retrieve"}}


def _analysis_schema() -> dict[str, Any]:
    relation = {"type": "object", "properties": {
        "feature_id": {"type": "string"}, "document_id": {"type": "string"},
        "relation": {"type": "string", "enum": ["full", "partial", "conflicting", "uncertain"]},
        "evidence_ids": {"type": "array", "items": {"type": "string"}},
        "quotes": {"type": "array", "items": {"type": "object", "properties": {
            "evidence_id": {"type": "string"}, "start": {"type": "integer"},
            "end": {"type": "integer"}, "text": {"type": "string"}},
            "required": ["evidence_id", "start", "end", "text"],
            "additionalProperties": False}},
    }, "required": ["feature_id", "document_id", "relation", "evidence_ids", "quotes"],
        "additionalProperties": False}
    return {"type": "object", "properties": {
        "schema_version": {"type": "integer", "enum": [1]},
        "relations": {"type": "array", "items": relation},
        "unresolved_feature_ids": {"type": "array", "items": {"type": "string"}},
    }, "required": ["schema_version", "relations", "unresolved_feature_ids"],
        "additionalProperties": False}


async def _analyst(provider: OllamaProvider, client: httpx.AsyncClient,
                   config: dict[str, Any]) -> dict[str, Any]:
    model = config["generation"]["analyst"]
    await _unload(client, model["model_id"])
    feature = "00000000-0000-4000-8000-000000000001"
    document = "00000000-0000-4000-8000-000000000002"
    evidence = "00000000-0000-4000-8000-000000000003"
    quote = "A cooling loop removes heat from a lithium-ion battery pack."
    prompt = ("Верни AnalysisV1. Сравни признак охлаждения батареи только с evidence. "
              "Не утверждай юридическую новизну. feature_id=" + feature +
              ", document_id=" + document + ", evidence_id=" + evidence +
              ", quote с offsets [0, " + str(len(quote)) + "]: " + quote +
              " Используй только указанные UUID и точную цитату.")
    calls: list[dict[str, Any]] = []
    for label in ("cold", "warm"):
        async def attempt(prompt_text: str, suffix: str,
                          phase_label: str = label) -> JsonResult | str:
            try:
                return await provider.complete_json(
                    model_id=model["model_id"], prompt_version="analysis-probe-v1",
                    request_id=phase_label + suffix, prompt=prompt_text, timeout=300,
                    schema=_analysis_schema(), max_output_tokens=model["max_output_tokens"],
                    reasoning_effort="low",
                )
            except InferenceProtocolError:
                return "INVALID_FINAL_JSON"

        first, timing = await _measure(attempt(prompt, ""))
        repair_attempted = isinstance(first, str)
        if repair_attempted:
            result, repair_timing = await _measure(attempt(
                "Предыдущая попытка нарушила JSON schema (INVALID_FINAL_JSON). "
                "Верни только полный AnalysisV1 JSON. " + prompt, "-repair"
            ))
        else:
            result, repair_timing = first, None
        if isinstance(result, str):
            calls.append({"phase": label, "schema_shape_valid": False,
                          "first_attempt_error_code": "INVALID_FINAL_JSON",
                          "repair_attempted": repair_attempted,
                          "repair_valid": False, "first_attempt": timing,
                          "repair": repair_timing})
            continue
        value = result.value
        relations = value.get("relations", [])
        valid_relation = len(relations) == 1 and all(
            relation.get("feature_id") == feature
            and relation.get("document_id") == document
            and relation.get("evidence_ids") == [evidence]
            and relation.get("quotes") == [{"evidence_id": evidence, "start": 0,
                                             "end": len(quote), "text": quote}]
            for relation in relations
        )
        calls.append({"phase": label, "schema_shape_valid":
                      value.get("schema_version") == 1
                      and isinstance(value.get("relations"), list)
                      and isinstance(value.get("unresolved_feature_ids"), list),
                      "relation_count": len(relations),
                      "citation_offsets_valid": valid_relation,
                      "raw_reasoning_in_result": "thinking" in json.dumps(value).lower(),
                      "first_attempt_error_code": "INVALID_FINAL_JSON" if repair_attempted
                      else None, "repair_attempted": repair_attempted,
                      "repair_valid": True if repair_attempted else None,
                      "validated_result_latency_ms": None,
                      "validated_result_latency_reason": "JOB-002_not_implemented",
                      "metadata": asdict(result.metadata), "first_attempt": timing,
                      "repair": repair_timing})
    await _unload(client, model["model_id"])
    return {"calls": calls}


async def _cancel_probe(provider: OllamaProvider, client: httpx.AsyncClient,
                        config: dict[str, Any]) -> dict[str, Any]:
    model = config["generation"]["analyst"]
    await _unload(client, model["model_id"])
    preload = await client.post("/api/generate", json={
        "model": model["model_id"], "prompt": "", "keep_alive": "5m", "stream": False,
    }, timeout=90)
    preload.raise_for_status()
    cancel = asyncio.Event()

    async def operation() -> Any:
        task = asyncio.create_task(provider.complete_json(
            model_id=model["model_id"], prompt_version="cancel-probe-v1", request_id="cancel",
            prompt="Объясни технические отличия в нескольких абзацах. Верни AnalysisV1.",
            timeout=120, schema=_analysis_schema(),
            max_output_tokens=model["max_output_tokens"], reasoning_effort="low",
            cancel=cancel,
        ))
        await asyncio.sleep(1)
        cancel.set()
        try:
            await task
            return "unexpected_success"
        except Exception as error:
            return type(error).__name__

    outcome, timing = await _measure(operation())
    loaded = [item["name"] for item in (await client.get("/api/ps")).json()["models"]]
    return {"outcome": outcome, "gate_blocked": provider.gate.blocked,
            "model_unloaded": model["model_id"] not in loaded, **timing}


async def _switch(provider: OllamaProvider, client: httpx.AsyncClient,
                   config: dict[str, Any]) -> dict[str, Any]:
    planner = config["generation"]["planner"]
    analyst = config["generation"]["analyst"]
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}},
              "required": ["ok"], "additionalProperties": False}
    calls = []
    for role, spec in (("planner_first", planner), ("analyst", analyst),
                       ("planner_after_analyst", planner)):
        await _unload(client, planner["model_id"])
        await _unload(client, analyst["model_id"])
        result, timing = await _measure(provider.complete_json(
            model_id=spec["model_id"], prompt_version="switch-probe-v1", request_id=role,
            prompt="Верни JSON с ok=true.", timeout=180, schema=schema,
            max_output_tokens=128,
            reasoning_effort="low" if spec is analyst else "default",
        ))
        loaded = [item["name"] for item in (await client.get("/api/ps")).json()["models"]]
        calls.append({"role": role, "valid": result.value.get("ok") is True,
                      "loaded_generators": [item for item in loaded if item in
                                            {planner["model_id"], analyst["model_id"]}],
                      "ttft_ms": result.metadata.model_ttft_ms, **timing})
    await _unload(client, planner["model_id"])
    await _unload(client, analyst["model_id"])
    return {"calls": calls}


async def _reranker(provider: OllamaProvider, reranker: LocalQwenReranker,
                    config: dict[str, Any]) -> dict[str, Any]:
    model_id = config["reranker"]["model_id"]
    query = "какое покрытие уменьшает растрескивание трубы при термоциклах"
    documents = ["A silica aerogel coating with ceramic mesh limits cracking "
                 "during thermal cycles.",
                 "A sodium-ion battery uses a water-based cathode binder.",
                 "A painting uses blue pigment."]
    calls = []
    for label in ("cold", "warm"):
        scores, timing = await _measure(provider.rerank(
            model_id=model_id, request_id=label, query=query, documents=documents,
            timeout=180,
        ), reranker=reranker)
        calls.append({"phase": label, "scores": scores,
                      "relevant_first": scores[0] > max(scores[1:]), **timing})
    cancel = asyncio.Event()
    cancel.set()
    cancelled = False
    try:
        await provider.rerank(model_id=model_id, request_id="cancel", query=query,
                              documents=documents, timeout=30, cancel=cancel)
    except Exception as error:
        cancelled = type(error).__name__ == "InferenceCancelled"
    timed_out = False
    try:
        await provider.rerank(model_id=model_id, request_id="timeout", query=query,
                              documents=documents, timeout=0.001)
    except Exception as error:
        timed_out = type(error).__name__ == "InferenceTimeout"
    await reranker.close()
    return {"calls": calls, "pre_cancel_rejected": cancelled,
            "short_deadline_timed_out": timed_out}


async def _mini(provider: OllamaProvider, client: httpx.AsyncClient,
                config: dict[str, Any]) -> dict[str, Any]:
    manifest = json.loads((ROOT / "eval/fixtures/manifest.json").read_text(encoding="utf-8"))
    cases = [json.loads(line) for line in (ROOT / "eval/cases/dev_smoke.jsonl")
             .read_text(encoding="utf-8").splitlines()]
    documents = manifest["documents"]
    ids = [item["external_id"] for item in documents]
    passages = [item["sections"][0]["text"] for item in documents]
    embedding_model = config["embedding"]["model_id"]
    vectors = await provider.embed(model_id=embedding_model, request_id="mini-docs",
                                   texts=passages, timeout=120)
    query_vectors = await provider.embed(model_id=embedding_model, request_id="mini-queries",
        texts=["Instruct: Retrieve relevant patent and scientific passages.\nQuery: "
               + item["query"] for item in cases], timeout=120)
    await _unload(client, embedding_model)

    def cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        return dot / (norm_a * norm_b)

    rows = []
    rerank_check: dict[str, Any] | None = None
    for case, query_vector in zip(cases, query_vectors, strict=True):
        ranked = sorted(range(len(ids)), key=lambda index: cosine(query_vector, vectors[index]),
                        reverse=True)
        expected = set(case["expected"]["expected_source_ids"])
        if not expected:
            continue
        found = [ids[index] for index in ranked]
        first = min(found.index(value) for value in expected) + 1
        rows.append({"case_id": case["case_id"], "recall_at_10":
                     len(expected.intersection(found[:10])) / len(expected),
                     "recall_at_20": len(expected.intersection(found[:20])) / len(expected),
                     "reciprocal_rank": 1 / first,
                     "top_3_hit": bool(expected.intersection(found[:3]))})
        if case["case_id"] == "EVAL000-DEV-008":
            candidates = ranked[:4]
            spec = config["reranker"]
            path = Path(snapshot_download(repo_id=spec["model_id"],
                revision=spec["revision"], local_files_only=True))
            reranker = LocalQwenReranker(model_id=spec["model_id"], model_path=path,
                                         max_length=spec["max_length"])
            try:
                scores = await reranker.score(model_id=spec["model_id"],
                    query=case["query"], documents=[passages[index] for index in candidates],
                    timeout=180, cancel=None)
            finally:
                await reranker.close()
            reordered = [candidates[index] for index in sorted(
                range(len(candidates)), key=lambda index: scores[index], reverse=True
            )]
            rerank_check = {"case_id": case["case_id"],
                            "candidate_source_ids": [ids[index] for index in candidates],
                            "reranked_source_ids": [ids[index] for index in reordered],
                            "top_1_hit_before": ids[candidates[0]] in expected,
                            "top_1_hit_after": ids[reordered[0]] in expected}
    return {"corpus_documents": len(ids), "evaluated_cases": len(rows),
            "recall_at_10": sum(row["recall_at_10"] for row in rows) / len(rows),
            "recall_at_20": sum(row["recall_at_20"] for row in rows) / len(rows),
            "mrr": sum(row["reciprocal_rank"] for row in rows) / len(rows),
            "top_3_hit_rate": sum(row["top_3_hit"] for row in rows) / len(rows),
            "cases": rows, "rerank_check": rerank_check}


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["inventory", "embedding", "planner", "analyst",
                                          "reranker", "mini", "cancel", "switch"])
    parser.add_argument("--output", type=Path,
                        default=ROOT / "docs/validation/LLM-002/measurements.json")
    args = parser.parse_args()
    config = _config()
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    report = json.loads(output.read_text(encoding="utf-8")) if output.exists() else {}
    async with httpx.AsyncClient(base_url=os.getenv("INFERENCE_BASE_URL", "http://127.0.0.1:11434"),
                                 timeout=360) as client:
        reranker = None
        if args.phase == "reranker":
            spec = config["reranker"]
            path = Path(snapshot_download(repo_id=spec["model_id"],
                                          revision=spec["revision"], local_files_only=True))
            reranker = LocalQwenReranker(model_id=spec["model_id"], model_path=path,
                                         max_length=spec["max_length"])
        provider = _provider(client, config, reranker=reranker)
        if args.phase == "inventory":
            result = await _inventory(client, config)
        elif args.phase == "embedding":
            result = await _embedding(provider, client, config)
        elif args.phase == "planner":
            result = await _planner(provider, client, config)
        elif args.phase == "analyst":
            result = await _analyst(provider, client, config)
        elif args.phase == "reranker":
            assert reranker is not None
            result = await _reranker(provider, reranker, config)
        elif args.phase == "cancel":
            result = await _cancel_probe(provider, client, config)
        elif args.phase == "switch":
            result = await _switch(provider, client, config)
        else:
            result = await _mini(provider, client, config)
    report[args.phase] = result
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"phase": args.phase, "result": result}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
