"""Контракты inference без деталей провайдера и его внутренних каналов."""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Literal, Protocol

ReasoningEffort = Literal["default", "low", "medium", "high"]


class InferenceError(Exception):
    """Типизированная ошибка без тела ответа провайдера."""


class InferenceConfigurationError(InferenceError):
    pass


class InferenceProtocolError(InferenceError):
    pass


class InferenceOutputLimit(InferenceProtocolError):
    """Ollama stopped generation at its configured output token limit."""

    def __init__(self, *, max_output_tokens: int) -> None:
        self.done_reason = "length"
        self.max_output_tokens = max_output_tokens
        super().__init__(
            "Ollama generation stopped at output limit "
            f"(done_reason=length, num_predict={max_output_tokens})"
        )


class InferenceTimeout(InferenceError):
    pass


class InferenceCancelled(InferenceError):
    pass


class InferenceUnavailable(InferenceError):
    pass


@dataclass(frozen=True)
class InferenceMetadata:
    provider: str
    model_id: str
    model_revision: str | None
    finish_reason: str | None
    model_ttft_ms: float | None
    model_ttft_reason: str | None
    reasoning_duration_ms: float | None
    reasoning_duration_reason: str | None
    reasoning_tokens: int | None
    reasoning_tokens_reason: str | None
    output_duration_ms: float | None
    output_duration_reason: str | None
    output_tokens: int | None
    output_tokens_reason: str | None
    total_ms: float
    load_ms: float | None
    load_reason: str | None


@dataclass(frozen=True)
class JsonResult:
    value: dict[str, Any]
    metadata: InferenceMetadata


class InferenceProvider(Protocol):
    async def complete_json(
        self,
        *,
        model_id: str,
        prompt_version: str,
        request_id: str,
        prompt: str,
        timeout: float,
        schema: dict[str, Any],
        max_output_tokens: int,
        context_window: int | None = None,
        reasoning_effort: ReasoningEffort = "default",
        thinking: bool | None = None,
        cancel: asyncio.Event | None = None,
    ) -> JsonResult: ...

    def stream_text(
        self,
        *,
        model_id: str,
        prompt_version: str,
        request_id: str,
        prompt: str,
        timeout: float,
        max_output_tokens: int,
        reasoning_effort: ReasoningEffort = "default",
        cancel: asyncio.Event | None = None,
    ) -> AsyncIterator[str]: ...

    async def embed(
        self,
        *,
        model_id: str,
        request_id: str,
        texts: list[str],
        timeout: float = 60,
        cancel: asyncio.Event | None = None,
    ) -> list[list[float]]: ...

    async def rerank(
        self,
        *,
        model_id: str,
        request_id: str,
        query: str,
        documents: list[str],
        timeout: float = 60,
        cancel: asyncio.Event | None = None,
    ) -> list[float]: ...
