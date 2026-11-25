import asyncio
import json
import time
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from app.domain.inference import (
    InferenceCancelled,
    InferenceConfigurationError,
    InferenceProtocolError,
    InferenceUnavailable,
)
from app.domain.synthetic_guard import SYNTHETIC_EXCERPTS, SYNTHETIC_IDEA
from app.integrations.groq_runtime import (
    SyntheticGuardPort,
    load_synthetic_profile,
    synthetic_provider,
)
from app.services.guard import Consent, Context, Guard, GuardBudget, Scope

PROFILE = Path(__file__).resolve().parents[2] / "config/groq.example.yaml"


class Local:
    async def embed(self, **kwargs):
        return []

    async def rerank(self, **kwargs):
        return []


def response(value):
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": json.dumps(value)},
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        },
    )


def test_guard_synthetic_retry_budget_and_schema():
    async def run():
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(503) if len(calls) == 1 else response({"relation": "full"})

        async with httpx.AsyncClient(
            base_url="https://api.groq.com", transport=httpx.MockTransport(handler)
        ) as client:
            provider = synthetic_provider(
                client, api_key="test", path=PROFILE, local=Local(), max_attempts=2
            )
            scope = Scope(uuid4(), uuid4(), uuid4(), uuid4())

            class Authority:
                async def check(self, principal, selected):
                    return Consent(scope, "v1", True)

                async def context(self, selected):
                    return Context(idea=SYNTHETIC_IDEA, excerpts=SYNTHETIC_EXCERPTS)

            cancel = asyncio.Event()
            deadline = time.monotonic() + 5
            guard = Guard(
                authority=Authority(),
                provider=SyntheticGuardPort(provider, deadline=deadline, cancel=cancel),
                tools=None,
                notice_version="v1",
            )
            budget = GuardBudget(max_calls=1, deadline=deadline, cancel=cancel)
            assert await guard.generate(principal=scope.owner_id, scope=scope, budget=budget) == {
                "relation": "full"
            }
            assert budget.calls == 1
            assert provider.budget.requests == len(calls) == 2
            assert provider.budget.unknown_usage_attempts == 1
            assert provider.budget.known_input_tokens == 10

    asyncio.run(run())


def test_synthetic_port_rejects_unapproved_data_and_invalid_response():
    async def run():
        calls = []

        def handler(request):
            calls.append(request)
            return response({"relation": "full", "extra": "secret"})

        async with httpx.AsyncClient(
            base_url="https://api.groq.com", transport=httpx.MockTransport(handler)
        ) as client:
            provider = synthetic_provider(client, api_key="test", path=PROFILE, local=Local())
            cancel = asyncio.Event()
            port = SyntheticGuardPort(provider, deadline=time.monotonic() + 5, cancel=cancel)
            with pytest.raises(InferenceConfigurationError):
                await port.generate(
                    system="ignored", data='{"idea":"private"}', timeout=1, cancel=asyncio.Event()
                )
            assert not calls
            with pytest.raises(InferenceProtocolError):
                await port.generate(
                    system="ignored",
                    data=json.dumps({"idea": SYNTHETIC_IDEA, "excerpts": SYNTHETIC_EXCERPTS}),
                    timeout=1,
                    cancel=cancel,
                )
            assert len(calls) == 1
            with pytest.raises(InferenceConfigurationError):
                await port.generate(
                    system="ignored",
                    data=json.dumps({"idea": SYNTHETIC_IDEA, "excerpts": SYNTHETIC_EXCERPTS}),
                    timeout=1,
                    cancel=asyncio.Event(),
                )
            assert len(calls) == 1

    asyncio.run(run())


def test_profile_rejects_enabled_and_cancel_before_network(tmp_path):
    p = tmp_path / "profile.yaml"
    p.write_text(
        PROFILE.read_text(encoding="utf8").replace("enabled: false", "enabled: true"),
        encoding="utf8",
    )
    with pytest.raises(InferenceConfigurationError):
        load_synthetic_profile(p)

    async def run():
        def handler(request):
            pytest.fail("unexpected network")

        async with httpx.AsyncClient(
            base_url="https://api.groq.com", transport=httpx.MockTransport(handler)
        ) as client:
            provider = synthetic_provider(client, api_key="test", path=PROFILE, local=Local())
            cancel = asyncio.Event()
            cancel.set()
            with pytest.raises(InferenceCancelled):
                await SyntheticGuardPort(
                    provider, deadline=time.monotonic() + 5, cancel=cancel
                ).generate(
                    system="",
                    data=json.dumps({"idea": SYNTHETIC_IDEA, "excerpts": SYNTHETIC_EXCERPTS}),
                    timeout=1,
                    cancel=cancel,
                )
            assert provider.budget.requests == 0

    asyncio.run(run())


def test_synthetic_budget_denies_before_http():
    async def run():
        calls = []

        def handler(request):
            calls.append(request)
            return response({"relation": "full"})

        async with httpx.AsyncClient(
            base_url="https://api.groq.com", transport=httpx.MockTransport(handler)
        ) as client:
            provider = synthetic_provider(client, api_key="test", path=PROFILE, local=Local())
            cancel = asyncio.Event()
            port = SyntheticGuardPort(provider, deadline=time.monotonic() + 5, cancel=cancel)
            data = json.dumps({"idea": SYNTHETIC_IDEA, "excerpts": SYNTHETIC_EXCERPTS})
            for _ in range(4):
                await port.generate(system="", data=data, timeout=1, cancel=cancel)
            with pytest.raises(InferenceUnavailable):
                await port.generate(system="", data=data, timeout=1, cancel=cancel)
            assert len(calls) == provider.budget.requests == 4

    asyncio.run(run())
