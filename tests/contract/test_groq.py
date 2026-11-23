"""Компонентные тесты Groq на mock HTTP; сеть и рабочий профиль не используются."""

import asyncio
import json
from decimal import Decimal

import httpx
import jsonschema
import pytest

from app.domain.inference import (
    InferenceCancelled,
    InferenceConfigurationError,
    InferenceProtocolError,
    InferenceTimeout,
    InferenceUnavailable,
)
from app.domain.planner import PlannerDraftV2
from app.integrations.groq import GroqBudget, GroqPrice, GroqProvider, GroqRole


class Validator:
    def check_schema(self, schema):
        jsonschema.Draft202012Validator.check_schema(schema)

    def validate(self, value, schema):
        jsonschema.Draft202012Validator(schema).validate(value)


class Local:
    async def embed(self, **kwargs):
        return [[1.0]]

    async def rerank(self, **kwargs):
        return [0.5]


def response(content='{"ok":true}', usage=True):
    payload = {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": content,
                    "reasoning": "PRIVATE_REASONING",
                },
            }
        ]
    }
    if usage:
        payload["usage"] = {"prompt_tokens": 10, "completion_tokens": 2}
    return httpx.Response(200, json=payload)


def make(client, budget=None, **kwargs):
    return GroqProvider(
        client,
        api_key="PRIVATE_KEY",
        roles={
            "planner": GroqRole("m", "v1", "json_schema", 2, 64, strict=True),
            "narrative": GroqRole("m", "v2", "text", 2, 64),
            "classifier": GroqRole("m", "v3", "json_object", 2, 64),
        },
        prices={"m": GroqPrice(Decimal("1"), Decimal("2"), "USD", "test tariff", "v1")},
        budget=budget or GroqBudget(20, 50000, Decimal("1")),
        validator=Validator(),
        local=Local(),
        **kwargs,
    )


def call(provider, **kwargs):
    args = dict(
        model_id="m",
        prompt_version="v1",
        request_id="r",
        prompt="PRIVATE_PROMPT",
        timeout=1,
        schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
        max_output_tokens=20,
    )
    args.update(kwargs)
    return provider.complete_json(**args)


def test_json_role_text_local_and_tariff():
    async def run():
        bodies = []

        def handler(request):
            bodies.append(json.loads(request.content))
            return response()

        async with httpx.AsyncClient(
            base_url="https://api.groq.com", transport=httpx.MockTransport(handler)
        ) as client:
            provider = make(client)
            result = await call(provider)
            assert result.value == {"ok": True}
            assert result.metadata.input_tokens == 10 and result.metadata.output_tokens == 2
            assert result.metadata.estimated_cost == "0.000014"
            assert (result.metadata.cost_currency, result.metadata.cost_version) == ("USD", "v1")
            assert "PRIVATE_REASONING" not in repr(result)
            assert bodies[0]["model"] == "m" and bodies[0]["max_completion_tokens"] == 20
            assert bodies[0]["response_format"]["json_schema"]["strict"] is True
            assert [
                x
                async for x in provider.stream_text(
                    model_id="m",
                    prompt_version="v2",
                    request_id="x",
                    prompt="x",
                    timeout=1,
                    max_output_tokens=20,
                )
            ] == ['{"ok":true}']
            assert await provider.embed(model_id="e", request_id="x", texts=["a"]) == [[1.0]]
            assert await provider.rerank(
                model_id="r", request_id="x", query="a", documents=["b"]
            ) == [0.5]

    asyncio.run(run())


@pytest.mark.parametrize(
    "content",
    ["", "PRIVATE invalid", "[]", '{"ok":"PRIVATE"}', "<think>PRIVATE</think>{}", '{"ok":NaN}'],
)
def test_bad_response_is_safe_and_not_retried(content):
    async def run():
        count = 0

        def handler(request):
            nonlocal count
            count += 1
            return response(content)

        async with httpx.AsyncClient(
            base_url="https://api.groq.com", transport=httpx.MockTransport(handler)
        ) as client:
            with pytest.raises(InferenceProtocolError) as error:
                await call(make(client))
            assert "PRIVATE" not in str(error.value) and count == 1

    asyncio.run(run())


def test_real_planner_schema_and_invalid_capability():
    async def run():
        count = 0

        def handler(request):
            nonlocal count
            count += 1
            return response("{}")

        async with httpx.AsyncClient(
            base_url="https://api.groq.com", transport=httpx.MockTransport(handler)
        ) as client:
            provider = make(client)
            with pytest.raises(InferenceProtocolError):
                await call(provider, schema=PlannerDraftV2.model_json_schema())
            with pytest.raises(InferenceConfigurationError):
                await call(provider, prompt_version="v2")
            with pytest.raises(InferenceConfigurationError):
                await call(provider, schema={"type": "not-a-type"})
            assert count == 1

    asyncio.run(run())


def test_retry_budget_unknown_usage_and_invalid_status():
    async def run():
        count = 0

        def handler(request):
            nonlocal count
            count += 1
            return (
                httpx.Response(429, headers={"Retry-After": "0"})
                if count == 1
                else response(usage=False)
            )

        budget = GroqBudget(2, 10000, Decimal("1"))
        async with httpx.AsyncClient(
            base_url="https://api.groq.com", transport=httpx.MockTransport(handler)
        ) as client:
            provider = make(client, budget, base_backoff=0)
            result = await call(provider, prompt_version="v3")
            assert result.metadata.attempts == 2 and result.metadata.estimated_cost is None
            assert result.metadata.estimated_cost_reason == "usage_incomplete"
            assert budget.requests == 2 and budget.unknown_usage_attempts == 2
            with pytest.raises(InferenceUnavailable):
                await call(provider)
            assert count == 2
        for status in (400, 401, 403):
            count = 0

            def denied(request, status=status):
                nonlocal count
                count += 1
                return httpx.Response(status, text="PRIVATE")

            async with httpx.AsyncClient(
                base_url="https://api.groq.com", transport=httpx.MockTransport(denied)
            ) as client:
                with pytest.raises(InferenceUnavailable) as error:
                    await call(make(client))
                assert count == 1 and "PRIVATE" not in str(error.value)

    asyncio.run(run())


def test_cancellation_deadline_backoff_queue_and_late_reply():
    async def run():
        calls = 0
        gate = asyncio.Event()

        async def handler(request):
            nonlocal calls
            calls += 1
            try:
                await gate.wait()
            except asyncio.CancelledError:
                await gate.wait()
            return response()

        async with httpx.AsyncClient(
            base_url="https://api.groq.com", transport=httpx.MockTransport(handler)
        ) as client:
            provider = make(client, max_parallel=1)
            with pytest.raises(InferenceTimeout):
                await call(provider, timeout=0.01)
            cancel = asyncio.Event()
            cancel.set()
            with pytest.raises(InferenceCancelled):
                await call(provider, cancel=cancel)
            with pytest.raises(InferenceTimeout):
                await call(provider, timeout=0.01)
            assert calls == 1 and provider.budget.requests == 1
            gate.set()
            await asyncio.sleep(0.01)
            assert provider.budget.requests == 1

        async def limited(request):
            return httpx.Response(429, headers={"Retry-After": "1"})

        async with httpx.AsyncClient(
            base_url="https://api.groq.com", transport=httpx.MockTransport(limited)
        ) as client:
            provider = make(client)
            with pytest.raises(InferenceTimeout):
                await call(provider, timeout=0.01)
            assert provider.budget.requests == 1 and provider.budget.unknown_usage_attempts == 1

    asyncio.run(run())


def test_response_size_and_concurrent_budget():
    async def run():
        count = 0

        async def handler(request):
            nonlocal count
            count += 1
            await asyncio.sleep(0)
            return response()

        async with httpx.AsyncClient(
            base_url="https://api.groq.com", transport=httpx.MockTransport(handler)
        ) as client:
            provider = make(client, GroqBudget(1, 10000, Decimal("1")), max_parallel=2)
            results = await asyncio.gather(call(provider), call(provider), return_exceptions=True)
            assert sum(isinstance(x, InferenceUnavailable) for x in results) == 1 and count == 1
            with pytest.raises(InferenceProtocolError):
                await call(make(client, max_response_bytes=10))

    asyncio.run(run())


def test_endpoint_redirect_external_schema_and_malformed_message():
    async def run():
        calls = []

        def handler(request):
            calls.append(str(request.url))
            return httpx.Response(307, headers={"Location": "https://attacker.test/steal"})

        async with httpx.AsyncClient(
            base_url="https://attacker.test", transport=httpx.MockTransport(handler)
        ) as client:
            with pytest.raises(InferenceConfigurationError):
                make(client)
        async with httpx.AsyncClient(
            base_url="https://api.groq.com",
            follow_redirects=True,
            transport=httpx.MockTransport(handler),
        ) as client:
            provider = make(client)
            with pytest.raises(InferenceConfigurationError):
                await call(provider, schema={"$ref": "https://attacker.test/schema"})
            assert calls == []
            with pytest.raises(InferenceUnavailable):
                await call(provider)
            assert calls == ["https://api.groq.com/openai/v1/chat/completions"]

        def malformed(request):
            return httpx.Response(
                200, json={"choices": [{"finish_reason": "stop", "message": "PRIVATE"}]}
            )

        async with httpx.AsyncClient(
            base_url="https://api.groq.com", transport=httpx.MockTransport(malformed)
        ) as client:
            with pytest.raises(InferenceProtocolError) as error:
                await call(make(client))
            assert "PRIVATE" not in str(error.value)

    asyncio.run(run())


def test_late_429_after_cancel_does_not_retry():
    async def run():
        calls = 0
        release = asyncio.Event()

        async def handler(request):
            nonlocal calls
            calls += 1
            try:
                await release.wait()
            except asyncio.CancelledError:
                await release.wait()
            return httpx.Response(429, headers={"Retry-After": "0"})

        async with httpx.AsyncClient(
            base_url="https://api.groq.com", transport=httpx.MockTransport(handler)
        ) as client:
            provider = make(client, base_backoff=0)
            with pytest.raises(InferenceTimeout):
                await call(provider, timeout=0.1)
            release.set()
            await asyncio.sleep(0.01)
            assert calls == 1 and provider.budget.requests == 1

    asyncio.run(run())


def test_currency_budget_and_cost_cap():
    price = GroqPrice(Decimal("1"), Decimal("2"), "USD", "test", "v1")
    budget = GroqBudget(5, 1000, Decimal("0.0001"))
    budget.reserve(10, 10, price)
    with pytest.raises(InferenceConfigurationError):
        budget.reserve(10, 10, GroqPrice(Decimal("1"), Decimal("2"), "EUR", "test", "v1"))
    with pytest.raises(InferenceUnavailable):
        budget.reserve(100, 10, price)
    assert budget.requests == 1


def test_existing_planner_and_narrative_schemas_on_mock_provider():
    from app.domain.contracts import AnalystNarrativeDraft

    planner = {
        "intent": "clarify",
        "add_features": [],
        "remove_features": [],
        "replace_features": [],
        "focus_source_ordinals": [],
        "suggested_retrieval": False,
        "confidence": 0.5,
    }
    narrative = {"schema_version": 1, "relations": []}

    async def run():
        outputs = iter([planner, narrative])

        def handler(request):
            return response(json.dumps(next(outputs)))

        async with httpx.AsyncClient(
            base_url="https://api.groq.com", transport=httpx.MockTransport(handler)
        ) as client:
            provider = make(client)
            plan = await call(provider, schema=PlannerDraftV2.model_json_schema())
            result = await call(
                provider, prompt_version="v3", schema=AnalystNarrativeDraft.model_json_schema()
            )
            assert PlannerDraftV2.model_validate(plan.value).confidence == 0.5
            assert AnalystNarrativeDraft.model_validate(result.value).relations == []

    asyncio.run(run())


def test_transient_transport_and_server_errors_retry_then_success():
    async def run():
        count = 0

        def handler(request):
            nonlocal count
            count += 1
            if count == 1:
                raise httpx.ConnectError("PRIVATE", request=request)
            if count == 2:
                return httpx.Response(503)
            return response()

        async with httpx.AsyncClient(
            base_url="https://api.groq.com", transport=httpx.MockTransport(handler)
        ) as client:
            provider = make(client, base_backoff=0)
            result = await call(provider)
            assert result.metadata.attempts == 3
            assert provider.budget.requests == 3
            assert provider.budget.unknown_usage_attempts == 2

    asyncio.run(run())


def test_stream_text_rejects_reply_after_blocking_parse_exceeds_deadline(monkeypatch):
    import time

    original_loads = json.loads

    def slow_loads(value, *args, **kwargs):
        if isinstance(value, bytearray):
            time.sleep(0.1)
        return original_loads(value, *args, **kwargs)

    async def run():
        async with httpx.AsyncClient(
            base_url="https://api.groq.com",
            transport=httpx.MockTransport(lambda request: response("LATE_CONTENT")),
        ) as client:
            provider = make(client)
            monkeypatch.setattr("app.integrations.groq.json.loads", slow_loads)
            chunks = []
            with pytest.raises(InferenceTimeout):
                async for chunk in provider.stream_text(
                    model_id="m",
                    prompt_version="v2",
                    request_id="late",
                    prompt="test",
                    timeout=0.05,
                    max_output_tokens=20,
                ):
                    chunks.append(chunk)
            assert chunks == []

    asyncio.run(run())
