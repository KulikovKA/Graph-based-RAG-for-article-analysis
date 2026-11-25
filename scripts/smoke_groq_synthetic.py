"""Изолированный smoke: по умолчанию mock HTTP; --live только с согласованным лимитом."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app.domain.contracts import AnalysisDraftV1, AnalystNarrativeDraft  # noqa: E402
from app.domain.planner import PlannerDraftV2  # noqa: E402
from app.integrations.groq_relation_synthetic import (  # noqa: E402
    SyntheticRelationResult,
    classify_synthetic_relation,
)
from app.integrations.groq_runtime import create_synthetic_runtime  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MODEL = "openai/gpt-oss-20b"
CASES = (
    (
        "planner",
        PlannerDraftV2,
        {
            "intent": "clarify",
            "add_features": [],
            "remove_features": [],
            "replace_features": [],
            "focus_source_ordinals": [],
            "suggested_retrieval": False,
            "confidence": 0.5,
        },
    ),
    (
        "analyst",
        AnalysisDraftV1,
        {"schema_version": 1, "relations": [], "unresolved_feature_ids": []},
    ),
    ("narrative", AnalystNarrativeDraft, {"schema_version": 1, "relations": []}),
    ("relation_classifier", SyntheticRelationResult, {"relation": "full"}),
)


class NoLocalCalls:
    async def embed(self, **kwargs):
        raise RuntimeError("local calls are outside this smoke")

    async def rerank(self, **kwargs):
        raise RuntimeError("local calls are outside this smoke")


async def run(live: bool) -> int:
    key = os.environ.get("GROQ_API_KEY", "") if live else "mock-key"
    if not key.strip():
        print("BLOCKED: GROQ_API_KEY отсутствует в среде процесса")
        return 2
    outputs = iter(case[2] for case in CASES)

    def mock_handler(request):
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": json.dumps(next(outputs))},
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )

    transport = None if live else httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(base_url="https://api.groq.com", transport=transport) as client:
        runtime = create_synthetic_runtime(
            client,
            api_key=key,
            path=ROOT / "config/groq.example.yaml",
            local=NoLocalCalls(),
        )
        provider, roles = runtime.provider, runtime.roles
        failures = 0
        for index, (name, schema, example) in enumerate(CASES):
            role = roles[name]
            try:
                if name == "relation_classifier":
                    classified = await classify_synthetic_relation(
                        provider,
                        model_id=role.model_id,
                        request_id=f"synthetic-{index}",
                        timeout=role.timeout,
                    )
                    if classified.relation != example["relation"]:
                        raise ValueError("unexpected synthetic classification")
                else:
                    result = await provider.complete_json(
                        model_id=role.model_id,
                        prompt_version=role.prompt_version,
                        request_id=f"synthetic-{index}",
                        prompt="Return this synthetic JSON object exactly: " + json.dumps(example),
                        timeout=role.timeout,
                        schema=schema.model_json_schema(),
                        max_output_tokens=512,
                        reasoning_effort="low" if name == "analyst" else "default",
                    )
                    schema.model_validate(result.value)
                print(f"PASS {name}/{schema.__name__}")
            except Exception as exc:
                failures += 1
                print(f"FAIL {name}/{schema.__name__}: {type(exc).__name__}")
        print(
            f"{'LIVE' if live else 'MOCK'}: requests={provider.budget.requests}, "
            f"reserved_tokens={provider.budget.reserved_tokens}, "
            f"reserved_usd={provider.budget.reserved_cost}, "
            f"known_input_tokens={provider.budget.known_input_tokens}, "
            f"known_output_tokens={provider.budget.known_output_tokens}, "
            f"known_estimated_usd={provider.budget.known_estimated_cost}, "
            f"unknown_usage_attempts={provider.budget.unknown_usage_attempts}, "
            f"tariff_version={runtime.prices[MODEL].version}"
        )
        print("NOT RUN: agent, extractor, judge; отсутствует Groq wiring")
        return int(bool(failures))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Сеть; лимит: 4 запроса и 0.02 USD")
    args = parser.parse_args()
    return asyncio.run(run(args.live))


if __name__ == "__main__":
    raise SystemExit(main())
