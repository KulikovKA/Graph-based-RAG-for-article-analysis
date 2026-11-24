"""Изолированный smoke: по умолчанию mock HTTP; --live только с согласованным лимитом."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

import httpx
import jsonschema
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app.domain.contracts import AnalysisDraftV1, AnalystNarrativeDraft  # noqa: E402
from app.domain.planner import PlannerDraftV2  # noqa: E402
from app.integrations.groq import GroqPrice, GroqProviderFactory, GroqRole  # noqa: E402
from app.integrations.groq_relation_synthetic import (  # noqa: E402
    SyntheticRelationResult,
    classify_synthetic_relation,
)

ROOT = Path(__file__).resolve().parents[1]
MODEL = "openai/gpt-oss-20b"
CASES = (
    ("planner", PlannerDraftV2, {"intent": "clarify", "add_features": [],
     "remove_features": [], "replace_features": [], "focus_source_ordinals": [],
     "suggested_retrieval": False, "confidence": 0.5}),
    ("analyst", AnalysisDraftV1, {"schema_version": 1, "relations": [],
                                 "unresolved_feature_ids": []}),
    ("narrative", AnalystNarrativeDraft, {"schema_version": 1, "relations": []}),
    ("relation_classifier", SyntheticRelationResult, {"relation": "full"}),
)


class Validator:
    def check_schema(self, schema):
        jsonschema.Draft202012Validator.check_schema(schema)

    def validate(self, value, schema):
        jsonschema.Draft202012Validator(schema).validate(value)


class NoLocalCalls:
    async def embed(self, **kwargs):
        raise RuntimeError("local calls are outside this smoke")

    async def rerank(self, **kwargs):
        raise RuntimeError("local calls are outside this smoke")


def load_profile():
    profile = yaml.safe_load((ROOT / "config/groq.example.yaml").read_text(encoding="utf-8"))
    roles = {}
    for name in ("planner", "analyst", "narrative", "relation_classifier"):
        role = profile["roles"][name]
        if role["model_id"] != MODEL or role["capability"] != "json_schema":
            raise ValueError("unexpected smoke model or capability")
        roles[name] = GroqRole(
            model_id=role["model_id"], prompt_version=role["prompt_version"],
            capability=role["capability"], timeout=min(float(role["timeout_seconds"]), 30),
            max_output_tokens=min(int(role["max_output_tokens"]), 512),
            reasoning_efforts=tuple(role.get("reasoning_efforts", [])),
        )
    row = profile["prices"][MODEL]
    # Запрещаем занизить резерв стоимости через изменённый конфиг.
    if (Decimal(row["input_per_million"]) != Decimal("0.075")
            or Decimal(row["output_per_million"]) != Decimal("0.30")
            or row["currency"] != "USD"):
        raise ValueError("smoke tariff changed; review budget before running")
    price = GroqPrice(Decimal("0.075"), Decimal("0.30"), "USD", row["source"], row["version"])
    return roles, {MODEL: price}


async def run(live: bool) -> int:
    roles, prices = load_profile()
    key = os.environ.get("GROQ_API_KEY", "") if live else "mock-key"
    if not key.strip():
        print("BLOCKED: GROQ_API_KEY отсутствует в среде процесса")
        return 2
    outputs = iter(case[2] for case in CASES)

    def mock_handler(request):
        return httpx.Response(200, json={
            "choices": [{"finish_reason": "stop", "message": {
                "role": "assistant", "content": json.dumps(next(outputs))}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        })

    transport = None if live else httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(base_url="https://api.groq.com", transport=transport) as client:
        provider = GroqProviderFactory(
            client, api_key=key, roles=roles, prices=prices, validator=Validator(),
            local=NoLocalCalls(), max_parallel=1, max_attempts=1,
        ).for_run(max_requests=4, max_tokens=50000, max_cost=Decimal("0.02"))
        failures = 0
        for index, (name, schema, example) in enumerate(CASES):
            role = roles[name]
            try:
                if name == "relation_classifier":
                    classified = await classify_synthetic_relation(
                        provider, model_id=role.model_id, request_id=f"synthetic-{index}",
                        timeout=role.timeout,
                    )
                    if classified.relation != example["relation"]:
                        raise ValueError("unexpected synthetic classification")
                else:
                    result = await provider.complete_json(
                        model_id=role.model_id, prompt_version=role.prompt_version,
                        request_id=f"synthetic-{index}",
                        prompt="Return this synthetic JSON object exactly: " + json.dumps(example),
                        timeout=role.timeout, schema=schema.model_json_schema(),
                        max_output_tokens=512,
                        reasoning_effort="low" if name == "analyst" else "default",
                    )
                    schema.model_validate(result.value)
                print(f"PASS {name}/{schema.__name__}")
            except Exception as exc:
                failures += 1
                print(f"FAIL {name}/{schema.__name__}: {type(exc).__name__}")
        print(f"{'LIVE' if live else 'MOCK'}: requests={provider.budget.requests}, "
              f"reserved_tokens={provider.budget.reserved_tokens}, "
              f"reserved_usd={provider.budget.reserved_cost}")
        print("NOT RUN: agent, extractor, judge; отсутствует Groq wiring")
        return int(bool(failures))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Сеть; лимит: 4 запроса и 0.02 USD")
    args = parser.parse_args()
    return asyncio.run(run(args.live))


if __name__ == "__main__":
    raise SystemExit(main())
