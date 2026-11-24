"""Проверки изолированного классификатора на mock HTTP, без живой модели."""

import asyncio
import json
import runpy
from decimal import Decimal
from pathlib import Path
from typing import get_args

import httpx
import jsonschema
import pytest

from app.domain.inference import InferenceCancelled, InferenceProtocolError
from app.integrations.groq import GroqBudget, GroqPrice, GroqProvider, GroqRole
from app.integrations.groq_relation_synthetic import (
    PROMPT_VERSION,
    RelationLabel,
    SyntheticRelationResult,
    classify_synthetic_relation,
)
from app.services.relation_classifier import RELATION_LABELS, RUBRIC


class Validator:
    def check_schema(self, schema):
        jsonschema.Draft202012Validator.check_schema(schema)

    def validate(self, value, schema):
        jsonschema.Draft202012Validator(schema).validate(value)


class Local:
    async def embed(self, **kwargs):
        raise AssertionError("unexpected embedding")

    async def rerank(self, **kwargs):
        raise AssertionError("unexpected rerank")


@pytest.mark.parametrize("payload", [
    {"relation": "PRIVATE_CANARY"},
    {"relation": "full", "probabilities": {"full": 1}},
    {"relation": "full", "confidence": 1},
    {},
])
def test_classifier_rejects_invalid_or_uncalibrated_output(payload):
    async def run():
        count = 0

        def handler(request):
            nonlocal count
            count += 1
            return httpx.Response(200, json={
                "choices": [{"finish_reason": "stop", "message": {
                    "role": "assistant", "content": json.dumps(payload)}}],
            })

        async with httpx.AsyncClient(
            base_url="https://api.groq.com", transport=httpx.MockTransport(handler)
        ) as client:
            provider = make_provider(client)
            with pytest.raises(InferenceProtocolError) as error:
                await classify_synthetic_relation(provider, model_id="test", request_id="r",
                                                  timeout=1)
            assert "PRIVATE_CANARY" not in str(error.value)
            assert count == 1

    asyncio.run(run())


def make_provider(client):
    return GroqProvider(
        client, api_key="mock-key",
        roles={"relation_classifier": GroqRole("test", PROMPT_VERSION, "json_schema", 2, 512)},
        prices={"test": GroqPrice(Decimal("1"), Decimal("2"), "USD", "test", "v1")},
        budget=GroqBudget(2, 10000, Decimal("1")), validator=Validator(), local=Local(),
        max_attempts=1,
    )


def test_classifier_uses_frozen_rubric_schema_and_no_probabilities():
    assert get_args(RelationLabel) == RELATION_LABELS

    async def run():
        bodies = []

        def handler(request):
            bodies.append(json.loads(request.content))
            return httpx.Response(200, json={
                "choices": [{"finish_reason": "stop", "message": {
                    "role": "assistant", "content": '{"relation":"full"}'}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 2},
            })

        async with httpx.AsyncClient(
            base_url="https://api.groq.com", transport=httpx.MockTransport(handler)
        ) as client:
            provider = make_provider(client)
            result = await classify_synthetic_relation(provider, model_id="test", request_id="r",
                                                        timeout=1)
            assert result == SyntheticRelationResult(relation="full")
            assert result.model_dump() == {"relation": "full"}
            body = bodies[0]
            assert json.dumps(RUBRIC, sort_keys=True) in body["messages"][0]["content"]
            schema = body["response_format"]["json_schema"]["schema"]
            assert schema["properties"]["relation"]["enum"] == list(RELATION_LABELS)
            assert schema["additionalProperties"] is False
            assert body["max_completion_tokens"] == 512 and provider.budget.requests == 1
            cancel = asyncio.Event()
            cancel.set()
            with pytest.raises(InferenceCancelled):
                await classify_synthetic_relation(provider, model_id="test", request_id="r",
                                                  timeout=1, cancel=cancel)
            assert len(bodies) == 1

    asyncio.run(run())


def test_mock_smoke_has_four_profiles_one_shared_budget_and_no_retries(monkeypatch, capsys):
    script = runpy.run_path(str(Path(__file__).resolve().parents[2] / "scripts" /
                                "smoke_groq_synthetic.py"))
    factory = script["GroqProviderFactory"]
    original = factory.for_run
    created = []

    def capture(self, **limits):
        provider = original(self, **limits)
        created.append((limits, provider))
        return provider

    monkeypatch.setattr(factory, "for_run", capture)
    assert asyncio.run(script["run"](False)) == 0
    limits, provider = created[0]
    assert limits == {"max_requests": 4, "max_tokens": 50000, "max_cost": Decimal("0.02")}
    assert provider.budget.requests == 4 and provider.budget.reserved_tokens <= 50000
    assert provider.budget.reserved_cost <= Decimal("0.02") and provider._attempts == 1
    profiles = script["load_profile"]()[0]
    assert set(profiles) == {"planner", "analyst", "narrative", "relation_classifier"}
    assert profiles["narrative"].prompt_version == "narrative_synthetic_v1"
    assert profiles["relation_classifier"].prompt_version == PROMPT_VERSION
    output = capsys.readouterr().out
    assert output.count("PASS ") == 4 and "MOCK: requests=4" in output
