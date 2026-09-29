"""Адаптер финального канала Ollama и подключаемый локальный reranker."""

import asyncio
import json
import math
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, Protocol, TypeVar

import httpx

from app.domain.inference import (
    InferenceCancelled,
    InferenceConfigurationError,
    InferenceMetadata,
    InferenceProtocolError,
    InferenceTimeout,
    InferenceUnavailable,
    JsonResult,
    ReasoningEffort,
)
from app.workers.inference import GenerationGate


class RerankerBackend(Protocol):
    async def score(self, *, model_id: str, query: str, documents: list[str],
                    timeout: float, cancel: asyncio.Event | None) -> list[float]: ...


T = TypeVar("T")


class OllamaProvider:
    def __init__(
        self, client: httpx.AsyncClient, *, gate: GenerationGate,
        model_revisions: dict[str, str],
        supported_efforts: dict[str, set[str]],
        reranker: RerankerBackend | None = None,
        generation_keep_alive: int | str = 0,
        embedding_keep_alive: int | str = 0,
        embedding_batch_size: int = 16,
    ) -> None:
        self.client = client
        self.gate = gate
        self.model_revisions = model_revisions
        self.supported_efforts = supported_efforts
        self.reranker = reranker
        self.generation_keep_alive = generation_keep_alive
        self.embedding_keep_alive = embedding_keep_alive
        if embedding_batch_size < 1 or embedding_batch_size > 64:
            raise InferenceConfigurationError("invalid embedding batch limit")
        self.embedding_batch_size = embedding_batch_size

    def _effort(self, model_id: str, effort: ReasoningEffort) -> str | bool | None:
        if model_id not in self.model_revisions:
            raise InferenceConfigurationError("unknown generation model")
        if effort == "default":
            return None
        if effort not in self.supported_efforts.get(model_id, set()):
            raise InferenceConfigurationError("reasoning effort is unsupported")
        return effort

    async def _confirm_unloaded(self, model_id: str) -> None:
        try:
            response = await self.client.post("/api/generate", json={
                "model": model_id, "prompt": "", "keep_alive": 0, "stream": False,
            }, timeout=5)
            response.raise_for_status()
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                state = await self.client.get("/api/ps", timeout=2)
                state.raise_for_status()
                if not any(item.get("name") == model_id
                           for item in state.json().get("models", [])):
                    return
                await asyncio.sleep(0.1)
        except (httpx.HTTPError, ValueError):
            pass
        self.gate.quarantine()
        raise InferenceUnavailable("backend stop was not confirmed")

    async def _frames(self, body: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        try:
            async with self.client.stream("POST", "/api/chat", json=body) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        frame = json.loads(line)
                    except (ValueError, TypeError):
                        raise InferenceProtocolError("invalid provider frame") from None
                    if not isinstance(frame, dict) or "error" in frame:
                        raise InferenceProtocolError("provider returned an invalid frame")
                    yield frame
        except httpx.TimeoutException:
            raise InferenceTimeout("inference transport timed out") from None
        except httpx.HTTPError:
            raise InferenceUnavailable("inference transport failed") from None

    @staticmethod
    def _content(frame: dict[str, Any]) -> tuple[str, bool]:
        message = frame.get("message", {})
        if not isinstance(message, dict) or set(message) - {"role", "content", "thinking"}:
            raise InferenceProtocolError("unsupported provider channel")
        if message.get("role", "assistant") != "assistant":
            raise InferenceProtocolError("unsupported provider role")
        content = message.get("content", "")
        thinking = message.get("thinking", "")
        if not isinstance(content, str) or not isinstance(thinking, str):
            raise InferenceProtocolError("invalid provider channel")
        if "<think" in content.lower() or "</think" in content.lower():
            raise InferenceProtocolError("unseparated reasoning in final channel")
        return content, bool(thinking)

    async def _generate(
        self, *, model_id: str, prompt: str, schema: dict[str, Any] | None,
        max_output_tokens: int, effort: ReasoningEffort,
        on_content: Callable[[str], Awaitable[None]] | None = None,
    ) -> tuple[list[str], InferenceMetadata]:
        think = self._effort(model_id, effort)
        if max_output_tokens < 1 or not prompt:
            raise InferenceConfigurationError("invalid generation request")
        body: dict[str, Any] = {
            "model": model_id, "messages": [{"role": "user", "content": prompt}],
            "stream": True, "keep_alive": self.generation_keep_alive,
            "options": {"num_predict": max_output_tokens,
                        "temperature": 0 if schema is not None else 0.2},
        }
        if schema is not None:
            body["format"] = schema
        if think is not None:
            body["think"] = think
        started = time.monotonic()
        first_token: float | None = None
        final_started: float | None = None
        pieces: list[str] = []
        terminal: dict[str, Any] | None = None
        try:
            async for frame in self._frames(body):
                content, thinking = self._content(frame)
                now = time.monotonic()
                if (content or thinking) and first_token is None:
                    first_token = now
                if content:
                    if final_started is None:
                        final_started = now
                    pieces.append(content)
                    if on_content is not None:
                        await on_content(content)
                if frame.get("done") is True:
                    if terminal is not None:
                        raise InferenceProtocolError("duplicate provider terminal frame")
                    terminal = frame
                elif terminal is not None:
                    raise InferenceProtocolError("provider data after terminal frame")
        except asyncio.CancelledError:
            await self._confirm_unloaded(model_id)
            raise
        if terminal is None:
            raise InferenceProtocolError("provider output was truncated")
        reason = terminal.get("done_reason")
        if reason != "stop":
            raise InferenceProtocolError("provider output did not finish")
        total_ms = (time.monotonic() - started) * 1000
        load_ms = terminal.get("load_duration")
        eval_count = terminal.get("eval_count")
        output_count_reliable = isinstance(eval_count, int) and first_token == final_started
        metadata = InferenceMetadata(
            provider="ollama", model_id=model_id,
            model_revision=self.model_revisions[model_id], finish_reason=reason,
            model_ttft_ms=(first_token - started) * 1000 if first_token else None,
            model_ttft_reason=None if first_token else "no_token_timing",
            reasoning_duration_ms=None, reasoning_duration_reason="not_reported_separately",
            reasoning_tokens=None, reasoning_tokens_reason="not_reported_separately",
            output_duration_ms=(time.monotonic() - final_started) * 1000
            if final_started else None,
            output_duration_reason=None if final_started else "no_final_token_timing",
            output_tokens=eval_count if output_count_reliable else None,
            output_tokens_reason=None if output_count_reliable
            else "provider_count_includes_reasoning_or_missing",
            total_ms=total_ms,
            load_ms=load_ms / 1_000_000 if isinstance(load_ms, int) else None,
            load_reason=None if isinstance(load_ms, int) else "not_reported",
        )
        return pieces, metadata

    async def complete_json(
        self, *, model_id: str, prompt_version: str, request_id: str, prompt: str,
        timeout: float, schema: dict[str, Any], max_output_tokens: int,
        reasoning_effort: ReasoningEffort = "default",
        cancel: asyncio.Event | None = None,
    ) -> JsonResult:
        self._effort(model_id, reasoning_effort)

        async def operation() -> tuple[list[str], InferenceMetadata]:
            return await self._generate(model_id=model_id, prompt=prompt, schema=schema,
                                        max_output_tokens=max_output_tokens,
                                        effort=reasoning_effort)

        pieces, metadata = await self.gate.run(operation, timeout=timeout, cancel=cancel)
        try:
            value = json.loads("".join(pieces))
        except (ValueError, TypeError):
            raise InferenceProtocolError("final output is not JSON") from None
        if not isinstance(value, dict):
            raise InferenceProtocolError("final output is not a JSON object")
        return JsonResult(value=value, metadata=metadata)

    async def stream_text(
        self, *, model_id: str, prompt_version: str, request_id: str, prompt: str,
        timeout: float, max_output_tokens: int,
        reasoning_effort: ReasoningEffort = "default",
        cancel: asyncio.Event | None = None,
    ) -> AsyncIterator[str]:
        self._effort(model_id, reasoning_effort)
        queue: asyncio.Queue[str | BaseException | None] = asyncio.Queue()

        async def publish(content: str) -> None:
            queue.put_nowait(content)

        async def produce() -> None:
            try:
                await self.gate.run(
                    lambda: self._generate(model_id=model_id, prompt=prompt, schema=None,
                                           max_output_tokens=max_output_tokens,
                                           effort=reasoning_effort, on_content=publish),
                    timeout=timeout, cancel=cancel,
                )
            except Exception as error:
                queue.put_nowait(error)
            finally:
                queue.put_nowait(None)

        producer = asyncio.create_task(produce())
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                if isinstance(item, BaseException):
                    raise item
                yield item
        finally:
            if not producer.done():
                producer.cancel()
            try:
                await producer
            except asyncio.CancelledError:
                pass

    async def embed(
        self, *, model_id: str, request_id: str, texts: list[str],
        timeout: float = 60, cancel: asyncio.Event | None = None,
    ) -> list[list[float]]:
        if not texts or any(not isinstance(value, str) or not value.strip() for value in texts):
            raise InferenceConfigurationError("embedding input must contain nonempty texts")
        if cancel is not None and cancel.is_set():
            raise InferenceCancelled("embedding cancelled")

        async def operation() -> list[list[float]]:
            all_vectors: list[list[float]] = []
            for start in range(0, len(texts), self.embedding_batch_size):
                batch = texts[start:start + self.embedding_batch_size]
                keep_alive = (self.embedding_keep_alive if start + len(batch) == len(texts)
                              else "1m")
                try:
                    response = await self.client.post("/api/embed", json={
                        "model": model_id, "input": batch, "keep_alive": keep_alive,
                    }, timeout=timeout)
                    response.raise_for_status()
                    data = response.json()
                except httpx.TimeoutException:
                    raise InferenceTimeout("embedding transport timed out") from None
                except (httpx.HTTPError, ValueError):
                    raise InferenceUnavailable("embedding transport failed") from None
                vectors = data.get("embeddings")
                if not isinstance(vectors, list) or len(vectors) != len(batch):
                    raise InferenceProtocolError("embedding count mismatch")
                if not all(isinstance(v, list) and v and all(
                    isinstance(x, float | int) and math.isfinite(x) for x in v
                ) for v in vectors):
                    raise InferenceProtocolError("invalid embedding vector")
                all_vectors.extend([float(x) for x in vector] for vector in vectors)
            if len({len(vector) for vector in all_vectors}) != 1:
                raise InferenceProtocolError("inconsistent embedding dimension")
            return all_vectors

        try:
            return await _run_optional_cancel(operation(), timeout=timeout, cancel=cancel)
        except (InferenceCancelled, InferenceTimeout, InferenceUnavailable):
            await self._confirm_unloaded(model_id)
            raise

    async def rerank(
        self, *, model_id: str, request_id: str, query: str, documents: list[str],
        timeout: float = 60, cancel: asyncio.Event | None = None,
    ) -> list[float]:
        if self.reranker is None:
            raise InferenceConfigurationError("reranker backend is not configured")
        if not query.strip() or not documents or any(not item.strip() for item in documents):
            raise InferenceConfigurationError("invalid reranking input")
        scores = await self.reranker.score(model_id=model_id, query=query,
                                           documents=documents, timeout=timeout, cancel=cancel)
        if len(scores) != len(documents) or any(not math.isfinite(score) for score in scores):
            raise InferenceProtocolError("invalid reranker scores")
        return scores


async def _run_optional_cancel(
    awaitable: Awaitable[T], *, timeout: float, cancel: asyncio.Event | None,
) -> T:
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    task = asyncio.ensure_future(awaitable)
    cancellation = asyncio.create_task(cancel.wait()) if cancel is not None else None
    try:
        waiting = {task, cancellation} if cancellation is not None else {task}
        done, _ = await asyncio.wait(waiting, timeout=timeout,
                                     return_when=asyncio.FIRST_COMPLETED)
        if cancellation is not None and cancellation in done:
            raise InferenceCancelled("inference cancelled")
        if task not in done:
            raise InferenceTimeout("inference deadline exceeded")
        return task.result()
    except (InferenceCancelled, InferenceTimeout):
        task.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(task), 5)
        except asyncio.CancelledError:
            pass
        except TimeoutError:
            raise InferenceUnavailable("inference stop was not confirmed") from None
        raise
    finally:
        if cancellation is not None:
            cancellation.cancel()
