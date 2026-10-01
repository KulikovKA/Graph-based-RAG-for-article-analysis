"""Контракты границы провайдера и слота генерации на fake backend."""

import asyncio
import json
from typing import Any

import httpx
import pytest

from app.domain.inference import (
    InferenceCancelled,
    InferenceConfigurationError,
    InferenceOutputLimit,
    InferenceProtocolError,
    InferenceTimeout,
    InferenceUnavailable,
)
from app.integrations.inference_http import OllamaProvider
from app.workers.inference import GenerationGate


def _frame(*, content: str = "", thinking: str = "", done: bool = False,
           reason: str = "stop") -> dict[str, Any]:
    frame: dict[str, Any] = {"message": {"role": "assistant", "content": content,
                                          "thinking": thinking}, "done": done}
    if done:
        frame.update({"done_reason": reason, "eval_count": 5,
                      "load_duration": 1_000_000})
    return frame


class FakeReranker:
    async def score(self, *, model_id: str, query: str, documents: list[str],
                    timeout: float, cancel: asyncio.Event | None) -> list[float]:
        return [float(query in item) for item in documents]


def _provider(frames: list[dict[str, Any]], *, base_url: str = "http://local-a",
              embedding_batch_size: int = 16) -> tuple[
    OllamaProvider, httpx.AsyncClient, list[str]
]:
    visited: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        visited.append(str(request.url))
        if request.url.path == "/api/embed":
            count = len(json.loads(request.content)["input"])
            return httpx.Response(200, json={"embeddings": [
                [float(index + 1), float(index + 2)] for index in range(count)
            ]})
        return httpx.Response(200, text="\n".join(json.dumps(frame) for frame in frames) + "\n")

    client = httpx.AsyncClient(base_url=base_url, transport=httpx.MockTransport(handler))
    provider = OllamaProvider(client, gate=GenerationGate(), model_revisions={"m": "digest"},
                              supported_efforts={"m": {"low", "medium"}},
                              reranker=FakeReranker(), embedding_batch_size=embedding_batch_size)
    return provider, client, visited


def test_final_channel_json_metadata_and_configurable_endpoint() -> None:
    async def exercise() -> None:
        provider, client, visited = _provider([
            _frame(thinking="RAW_PRIVATE_REASONING"),
            _frame(content='{"ok":'), _frame(content="true}"), _frame(done=True),
        ], base_url="http://replaceable-endpoint")
        try:
            result = await provider.complete_json(
                model_id="m", prompt_version="v1", request_id="r1", prompt="check",
                timeout=2, schema={"type": "object"}, max_output_tokens=32,
                reasoning_effort="low",
            )
            assert result.value == {"ok": True}
            assert result.metadata.model_ttft_ms is not None
            assert result.metadata.reasoning_tokens is None
            assert result.metadata.reasoning_tokens_reason is not None
            assert "RAW_PRIVATE_REASONING" not in repr(result)
            assert visited == ["http://replaceable-endpoint/api/chat"]
            chunks = [chunk async for chunk in provider.stream_text(
                model_id="m", prompt_version="v1", request_id="r2", prompt="check",
                timeout=2, max_output_tokens=32)]
            assert chunks == ['{"ok":', "true}"]
            assert await provider.rerank(model_id="rerank", request_id="r", query="patent",
                documents=["other", "patent claim"]) == [0.0, 1.0]
            assert await provider.embed(model_id="embed", request_id="r",
                                        texts=["русский", "English"]) == [[1.0, 2.0], [2.0, 3.0]]
        finally:
            await client.aclose()

    asyncio.run(exercise())


@pytest.mark.parametrize("frames", [
    [_frame(content="<think>PRIVATE</think>{}") , _frame(done=True)],
    [_frame(content='{"ok":true}')],
    [_frame(content='{"ok":true}'), _frame(done=True, reason="length")],
    [{"message": {"content": "{}", "analysis": "PRIVATE"}, "done": False}, _frame(done=True)],
])
def test_invalid_channels_and_truncation_never_expose_raw_data(
    frames: list[dict[str, Any]],
) -> None:
    async def exercise() -> None:
        provider, client, _ = _provider(frames)
        try:
            with pytest.raises(InferenceProtocolError) as error:
                await provider.complete_json(model_id="m", prompt_version="v1",
                    request_id="r", prompt="check", timeout=2,
                    schema={"type": "object"}, max_output_tokens=32)
            assert "PRIVATE" not in str(error.value)
        finally:
            await client.aclose()

    asyncio.run(exercise())


def test_ollama_length_done_reason_is_a_typed_output_limit() -> None:
    async def exercise() -> None:
        provider, client, _ = _provider([
            _frame(content='{"partial":'), _frame(done=True, reason="length")
        ])
        try:
            with pytest.raises(InferenceOutputLimit) as error:
                await provider.complete_json(
                    model_id="m", prompt_version="v1", request_id="length-run",
                    prompt="check", timeout=2, schema={"type": "object"},
                    max_output_tokens=536,
                )
            assert error.value.done_reason == "length"
            assert error.value.max_output_tokens == 536
            assert "done_reason=length" in str(error.value)
            assert "num_predict=536" in str(error.value)
        finally:
            await client.aclose()

    asyncio.run(exercise())


def test_non_length_done_reason_is_preserved_in_protocol_error() -> None:
    async def exercise() -> None:
        provider, client, _ = _provider([_frame(content="{}"), _frame(done=True, reason="other")])
        try:
            with pytest.raises(InferenceProtocolError, match="done_reason='other'"):
                await provider.complete_json(
                    model_id="m", prompt_version="v1", request_id="other-run",
                    prompt="check", timeout=2, schema={"type": "object"},
                    max_output_tokens=536,
                )
        finally:
            await client.aclose()

    asyncio.run(exercise())


def test_graph_options_are_request_scoped_and_other_requests_omit_context_window() -> None:
    async def exercise() -> None:
        bodies: list[dict[str, Any]] = []
        timeouts: list[float] = []

        def handler(request: httpx.Request) -> httpx.Response:
            bodies.append(json.loads(request.content))
            frames = [_frame(content='{"ok":true}'), _frame(done=True)]
            return httpx.Response(
                200, text="\n".join(json.dumps(frame) for frame in frames) + "\n"
            )

        class CapturingGate:
            async def run(self, operation, *, timeout, cancel=None):  # type: ignore[no-untyped-def]
                timeouts.append(timeout)
                return await operation()

        async with httpx.AsyncClient(
            base_url="http://graph-profile", transport=httpx.MockTransport(handler)
        ) as client:
            provider = OllamaProvider(
                client, gate=CapturingGate(), model_revisions={"m": "digest"},
                supported_efforts={},
            )
            await provider.complete_json(
                model_id="m", prompt_version="graph-v2", request_id="graph-profile",
                prompt="graph", timeout=300, schema={"type": "object"},
                max_output_tokens=2048, context_window=16384,
            )
            await provider.complete_json(
                model_id="m", prompt_version="planner-v1", request_id="planner-profile",
                prompt="plan", timeout=30, schema={"type": "object"},
                max_output_tokens=384,
            )

        assert bodies[0]["options"] == {
            "num_predict": 2048, "temperature": 0, "num_ctx": 16384,
        }
        assert bodies[1]["options"] == {"num_predict": 384, "temperature": 0}
        assert timeouts == [300, 30]

    asyncio.run(exercise())


def test_unsupported_effort_fails_before_transport() -> None:
    async def exercise() -> None:
        provider, client, visited = _provider([_frame(content="{}"), _frame(done=True)])
        try:
            with pytest.raises(InferenceConfigurationError):
                await provider.complete_json(model_id="m", prompt_version="v1",
                    request_id="r", prompt="check", timeout=2,
                    schema={"type": "object"}, max_output_tokens=32,
                    reasoning_effort="high")
            assert visited == []
        finally:
            await client.aclose()

    asyncio.run(exercise())


def test_embedding_batches_are_bounded() -> None:
    async def exercise() -> None:
        provider, client, visited = _provider([], embedding_batch_size=1)
        try:
            vectors = await provider.embed(model_id="embed", request_id="r",
                                           texts=["first", "second"])
            assert vectors == [[1.0, 2.0], [1.0, 2.0]]
            assert visited == ["http://local-a/api/embed", "http://local-a/api/embed"]
        finally:
            await client.aclose()

    asyncio.run(exercise())


def test_gate_timeout_cancel_late_response_and_independent_heartbeat() -> None:
    async def exercise() -> None:
        gate = GenerationGate(waiting_capacity=1, stop_grace=0.02)
        beats = 0

        async def heartbeat() -> None:
            nonlocal beats
            beats += 1

        async def slow() -> str:
            await asyncio.sleep(5)
            return "late secret"

        with pytest.raises(InferenceTimeout):
            await gate.run(slow, timeout=0.02, heartbeat=heartbeat)
        assert beats > 0
        assert await gate.run(lambda: asyncio.sleep(0, result="next"), timeout=1) == "next"
        cancel = asyncio.Event()
        cancel.set()
        with pytest.raises(InferenceCancelled):
            await gate.run(slow, timeout=1, cancel=cancel)
        assert await gate.run(lambda: asyncio.sleep(0, result="released"), timeout=1) == "released"

        async def ignores_cancel() -> str:
            try:
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                await asyncio.sleep(0.1)
            return "late secret"

        with pytest.raises(InferenceTimeout):
            await gate.run(ignores_cancel, timeout=0.02)
        assert gate.blocked
        with pytest.raises(InferenceUnavailable):
            await gate.run(slow, timeout=1)
        await asyncio.sleep(0.12)
        gate.recover()
        recovered = await gate.run(lambda: asyncio.sleep(0, result="recovered"), timeout=1)
        assert recovered == "recovered"

    asyncio.run(exercise())
