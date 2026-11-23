"""Изолированный Groq-адаптер; включение в рабочий профиль требует I-SEC."""

import asyncio
import json
import math
import random
import threading
import time
from collections.abc import AsyncIterator, Awaitable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from email.utils import parsedate_to_datetime
from typing import Any, Literal, Protocol, TypeVar

import httpx

from app.domain.inference import (
    InferenceCancelled,
    InferenceConfigurationError,
    InferenceMetadata,
    InferenceProtocolError,
    InferenceProvider,
    InferenceTimeout,
    InferenceUnavailable,
    JsonResult,
    ReasoningEffort,
)


class SchemaValidator(Protocol):
    def check_schema(self, schema: dict[str, Any]) -> None: ...
    def validate(self, value: dict[str, Any], schema: dict[str, Any]) -> None: ...


@dataclass(frozen=True)
class GroqRole:
    model_id: str
    prompt_version: str
    capability: Literal["json_schema", "json_object", "text"]
    timeout: float
    max_output_tokens: int
    revision: str | None = None
    strict: bool = False


@dataclass(frozen=True)
class GroqPrice:
    input_per_million: Decimal
    output_per_million: Decimal
    currency: str
    source: str
    version: str

    def cost(self, input_tokens: int, output_tokens: int) -> Decimal:
        return (
            self.input_per_million * input_tokens + self.output_per_million * output_tokens
        ) / Decimal(1000000)


@dataclass
class GroqBudget:
    """Единый экземпляр передаётся всем вызовам одного анализа.

    Неизвестный расход удерживает весь резерв. Резерв намеренно не освобождается
    даже для известного usage: это консервативная политика лимита анализа.
    """

    max_requests: int
    max_tokens: int
    max_cost: Decimal
    requests: int = 0
    reserved_tokens: int = 0
    reserved_cost: Decimal = Decimal(0)
    known_input_tokens: int = 0
    known_output_tokens: int = 0
    unknown_usage_attempts: int = 0
    known_estimated_cost: Decimal = Decimal(0)
    _exhausted: bool = field(default=False, init=False, repr=False)
    _currency: str | None = field(default=None, init=False, repr=False)
    _pending: set[int] = field(default_factory=set, repr=False)
    _lock: Any = field(default_factory=threading.Lock, repr=False)

    def reserve(self, input_tokens: int, output_tokens: int, price: GroqPrice) -> int:
        cost = price.cost(input_tokens, output_tokens)
        with self._lock:
            if self._currency is not None and self._currency != price.currency:
                raise InferenceConfigurationError("inconsistent budget currency")
            if (
                self._exhausted
                or self.requests >= self.max_requests
                or self.reserved_tokens + input_tokens + output_tokens > self.max_tokens
                or self.reserved_cost + cost > self.max_cost
            ):
                raise InferenceUnavailable("inference budget exhausted")
            self._currency = price.currency
            self.requests += 1
            self.reserved_tokens += input_tokens + output_tokens
            self.reserved_cost += cost
            self._pending.add(self.requests)
            return self.requests

    def settle(
        self, attempt: int, input_tokens: int | None, output_tokens: int | None, price: GroqPrice
    ) -> None:
        with self._lock:
            if attempt not in self._pending:
                return
            self._pending.remove(attempt)
            if input_tokens is not None:
                self.known_input_tokens += input_tokens
            if output_tokens is not None:
                self.known_output_tokens += output_tokens
            if input_tokens is None or output_tokens is None:
                self.unknown_usage_attempts += 1
                return
            self.known_estimated_cost += price.cost(input_tokens, output_tokens)


T = TypeVar("T")


class GroqProvider:
    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        api_key: str,
        roles: dict[str, GroqRole],
        prices: dict[str, GroqPrice],
        budget: GroqBudget,
        validator: SchemaValidator,
        local: InferenceProvider,
        max_parallel: int = 2,
        max_attempts: int = 3,
        max_response_bytes: int = 1_000_000,
        max_request_bytes: int = 200_000,
        base_backoff: float = 0.1,
        max_backoff: float = 5.0,
    ) -> None:
        if (
            not api_key
            or str(client.base_url) not in {"https://api.groq.com", "https://api.groq.com/"}
            or not roles
            or max_parallel < 1
            or max_attempts < 1
            or max_attempts > 10
            or max_response_bytes < 1
            or max_request_bytes < 1
            or base_backoff < 0
            or max_backoff < 0
            or budget.max_requests < 1
            or budget.max_tokens < 1
            or not budget.max_cost.is_finite()
            or budget.max_cost < 0
        ):
            raise InferenceConfigurationError("invalid provider configuration")
        for role in roles.values():
            price = prices.get(role.model_id)
            if (
                not role.model_id
                or not role.prompt_version
                or role.capability not in {"text", "json_object", "json_schema"}
                or not math.isfinite(role.timeout)
                or role.timeout <= 0
                or role.max_output_tokens < 1
                or (role.strict and role.capability != "json_schema")
                or price is None
                or not price.input_per_million.is_finite()
                or price.input_per_million < 0
                or not price.output_per_million.is_finite()
                or price.output_per_million < 0
                or not price.currency
                or not price.source
                or not price.version
            ):
                raise InferenceConfigurationError("invalid role or price configuration")
        bindings = [(r.model_id, r.prompt_version) for r in roles.values()]
        if len(bindings) != len(set(bindings)):
            raise InferenceConfigurationError("ambiguous role configuration")
        self._client, self._api_key, self._roles, self._prices = (
            client,
            api_key,
            roles.copy(),
            prices.copy(),
        )
        self.budget, self._validator, self._local = budget, validator, local
        self._slots = asyncio.Semaphore(max_parallel)
        self._attempts, self._response_limit, self._request_limit = (
            max_attempts,
            max_response_bytes,
            max_request_bytes,
        )
        self._base_backoff, self._max_backoff = base_backoff, max_backoff

    def _role(
        self,
        model_id: str,
        prompt_version: str,
        json_mode: bool,
        timeout: float,
        max_output_tokens: int,
        effort: ReasoningEffort,
    ) -> GroqRole:
        matches = [
            r
            for r in self._roles.values()
            if (r.model_id, r.prompt_version) == (model_id, prompt_version)
        ]
        if (
            len(matches) != 1
            or not math.isfinite(timeout)
            or timeout <= 0
            or max_output_tokens < 1
            or effort != "default"
        ):
            raise InferenceConfigurationError("unsupported generation request")
        role = matches[0]
        if (
            max_output_tokens > role.max_output_tokens
            or (json_mode and role.capability == "text")
            or (not json_mode and role.capability != "text")
        ):
            raise InferenceConfigurationError("unsupported role capability or limit")
        return role

    async def _bounded(
        self,
        operation: Awaitable[T],
        timeout: float,
        cancel: asyncio.Event | None,
        aborted: asyncio.Event,
    ) -> T:
        if cancel is not None and cancel.is_set():
            if hasattr(operation, "close"):
                operation.close()
            raise InferenceCancelled("inference cancelled")
        task = asyncio.ensure_future(operation)
        signal = asyncio.create_task(cancel.wait()) if cancel is not None else None
        try:
            waiters: set[asyncio.Future[Any]] = {task}
            if signal is not None:
                waiters.add(signal)
            done, _ = await asyncio.wait(
                waiters, timeout=timeout, return_when=asyncio.FIRST_COMPLETED
            )
            if signal is not None and signal in done:
                if task.done():
                    self._discard(task)
                raise InferenceCancelled("inference cancelled")
            if task not in done:
                raise InferenceTimeout("inference deadline exceeded")
            return task.result()
        finally:
            if signal is not None:
                signal.cancel()
            if not task.done():
                aborted.set()
                task.cancel()
                task.add_done_callback(self._discard)

    @staticmethod
    def _discard(task: asyncio.Future[Any]) -> None:
        if not task.cancelled():
            task.exception()

    @staticmethod
    def _retry_after(value: str | None) -> float | None:
        if not value:
            return None
        try:
            seconds = float(value)
            if not math.isfinite(seconds) or seconds < 0:
                return None
            return seconds
        except ValueError:
            try:
                date = parsedate_to_datetime(value)
                if date.tzinfo is None:
                    return None
                return max(0.0, (date - datetime.now(UTC)).total_seconds())
            except (ValueError, TypeError, OverflowError):
                return None

    async def _request(
        self,
        body: dict[str, Any],
        price: GroqPrice,
        input_reserve: int,
        output_reserve: int,
        aborted: asyncio.Event,
    ) -> tuple[dict[str, Any], int]:
        async with self._slots:
            for index in range(self._attempts):
                if aborted.is_set():
                    raise InferenceCancelled("inference cancelled")
                attempt = self.budget.reserve(input_reserve, output_reserve, price)
                retry_after = None
                try:
                    async with self._client.stream(
                        "POST",
                        "/openai/v1/chat/completions",
                        json=body,
                        follow_redirects=False,
                        headers={"Authorization": "Bearer " + self._api_key},
                    ) as response:
                        status = response.status_code
                        if status == 429 or 500 <= status <= 599:
                            retry_after = self._retry_after(response.headers.get("Retry-After"))
                        elif status != 200:
                            raise InferenceUnavailable("inference provider rejected request")
                        else:
                            raw = bytearray()
                            async for chunk in response.aiter_bytes():
                                if len(raw) + len(chunk) > self._response_limit:
                                    raise InferenceProtocolError("provider response exceeds limit")
                                raw.extend(chunk)
                            try:
                                payload = json.loads(raw)
                            except (ValueError, UnicodeDecodeError):
                                raise InferenceProtocolError("invalid provider response") from None
                            if not isinstance(payload, dict):
                                raise InferenceProtocolError("invalid provider response")
                            usage = payload.get("usage")
                            inp = usage.get("prompt_tokens") if isinstance(usage, dict) else None
                            out = (
                                usage.get("completion_tokens") if isinstance(usage, dict) else None
                            )
                            inp = inp if type(inp) is int and inp >= 0 else None
                            out = out if type(out) is int and out >= 0 else None
                            self.budget.settle(attempt, inp, out, price)
                            if (inp is not None and inp > input_reserve) or (
                                out is not None and out > output_reserve
                            ):
                                with self.budget._lock:
                                    self.budget._exhausted = True
                                raise InferenceProtocolError("provider usage exceeded reservation")
                            return payload, index + 1
                except httpx.HTTPError:
                    pass
                finally:
                    self.budget.settle(attempt, None, None, price)
                if aborted.is_set():
                    raise InferenceCancelled("inference cancelled")
                if index + 1 >= self._attempts:
                    break
                delay = min(self._max_backoff, self._base_backoff * (2**index))
                delay = max(random.uniform(0, delay), retry_after or 0)
                if delay > self._max_backoff:
                    raise InferenceUnavailable("provider retry delay exceeds limit")
                await asyncio.sleep(delay)
            raise InferenceUnavailable("inference provider unavailable")

    @staticmethod
    def _check_local_schema(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {"$id", "$dynamicRef", "$recursiveRef"}:
                    raise ValueError("unsupported schema reference")
                if key == "$ref" and (not isinstance(child, str) or not child.startswith("#/")):
                    raise ValueError("external schema reference")
                GroqProvider._check_local_schema(child)
        elif isinstance(value, list):
            for child in value:
                GroqProvider._check_local_schema(child)

    async def _generate(
        self,
        *,
        role: GroqRole,
        prompt: str,
        timeout: float,
        max_output_tokens: int,
        schema: dict[str, Any] | None,
        cancel: asyncio.Event | None,
    ) -> tuple[str, InferenceMetadata]:
        started = time.monotonic()
        if not prompt:
            raise InferenceConfigurationError("empty inference request")
        body: dict[str, Any] = {
            "model": role.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_completion_tokens": max_output_tokens,
            "stream": False,
        }
        if schema is not None:
            try:
                self._check_local_schema(schema)
                self._validator.check_schema(schema)
            except Exception:
                raise InferenceConfigurationError("invalid JSON schema") from None
            if role.capability == "json_schema":
                body["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "domain_result",
                        "strict": role.strict,
                        "schema": schema,
                    },
                }
            else:
                body["response_format"] = {"type": "json_object"}
        try:
            encoded = json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8")
        except (TypeError, ValueError):
            raise InferenceConfigurationError("invalid generation request") from None
        if len(encoded) > self._request_limit:
            raise InferenceConfigurationError("inference request exceeds limit")
        price = self._prices[role.model_id]
        remaining = min(timeout, role.timeout) - (time.monotonic() - started)
        if remaining <= 0:
            raise InferenceTimeout("inference deadline exceeded")
        aborted = asyncio.Event()
        payload, attempts = await self._bounded(
            self._request(body, price, len(encoded), max_output_tokens, aborted),
            remaining,
            cancel,
            aborted,
        )
        try:
            choices = payload["choices"]
            if not isinstance(choices, list) or len(choices) != 1:
                raise ValueError
            choice = choices[0]
            if choice["finish_reason"] != "stop":
                raise ValueError
            message = choice["message"]
            if not isinstance(message, dict):
                raise ValueError
            if message.get("role") != "assistant" or set(message) - {
                "role",
                "content",
                "reasoning",
            }:
                raise ValueError
            content = message["content"]
            if (
                not isinstance(content, str)
                or not content.strip()
                or "<think" in content.lower()
                or "</think" in content.lower()
            ):
                raise ValueError
        except (KeyError, TypeError, ValueError):
            raise InferenceProtocolError("invalid provider final content") from None
        usage = payload.get("usage")
        inp = usage.get("prompt_tokens") if isinstance(usage, dict) else None
        out = usage.get("completion_tokens") if isinstance(usage, dict) else None
        inp = inp if type(inp) is int and inp >= 0 else None
        out = out if type(out) is int and out >= 0 else None
        cost = str(price.cost(inp, out)) if inp is not None and out is not None else None
        metadata = InferenceMetadata(
            provider="groq",
            model_id=role.model_id,
            model_revision=role.revision,
            finish_reason="stop",
            model_ttft_ms=None,
            model_ttft_reason="not_streamed",
            reasoning_duration_ms=None,
            reasoning_duration_reason="not_reported_separately",
            reasoning_tokens=None,
            reasoning_tokens_reason="not_reported_separately",
            output_duration_ms=None,
            output_duration_reason="not_reported_separately",
            output_tokens=out,
            output_tokens_reason=None if out is not None else "not_reported",
            total_ms=(time.monotonic() - started) * 1000,
            load_ms=None,
            load_reason="not_reported",
            input_tokens=inp,
            input_tokens_reason=None if inp is not None else "not_reported",
            estimated_cost=cost,
            estimated_cost_reason=None if cost is not None else "usage_incomplete",
            cost_currency=price.currency,
            cost_source=price.source,
            cost_version=price.version,
            attempts=attempts,
        )
        return content, metadata

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
    ) -> JsonResult:
        started = time.monotonic()
        role = self._role(
            model_id, prompt_version, True, timeout, max_output_tokens, reasoning_effort
        )
        if thinking is not None or context_window is not None:
            raise InferenceConfigurationError("unsupported generation option")
        content, metadata = await self._generate(
            role=role,
            prompt=prompt,
            timeout=timeout,
            max_output_tokens=max_output_tokens,
            schema=schema,
            cancel=cancel,
        )
        try:
            value = json.loads(
                content, parse_constant=lambda _: (_ for _ in ()).throw(ValueError())
            )
            if not isinstance(value, dict):
                raise ValueError
            self._validator.validate(value, schema)
        except Exception:
            raise InferenceProtocolError("invalid structured provider output") from None
        if cancel is not None and cancel.is_set():
            raise InferenceCancelled("inference cancelled")
        if time.monotonic() - started >= min(timeout, role.timeout):
            raise InferenceTimeout("inference deadline exceeded")
        return JsonResult(value=value, metadata=metadata)

    async def stream_text(
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
    ) -> AsyncIterator[str]:
        started = time.monotonic()
        role = self._role(
            model_id, prompt_version, False, timeout, max_output_tokens, reasoning_effort
        )
        content, _ = await self._generate(
            role=role,
            prompt=prompt,
            timeout=timeout,
            max_output_tokens=max_output_tokens,
            schema=None,
            cancel=cancel,
        )
        if cancel is not None and cancel.is_set():
            raise InferenceCancelled("inference cancelled")
        if time.monotonic() - started >= min(timeout, role.timeout):
            raise InferenceTimeout("inference deadline exceeded")
        yield content

    async def embed(
        self,
        *,
        model_id: str,
        request_id: str,
        texts: list[str],
        timeout: float = 60,
        cancel: asyncio.Event | None = None,
    ) -> list[list[float]]:
        return await self._local.embed(
            model_id=model_id, request_id=request_id, texts=texts, timeout=timeout, cancel=cancel
        )

    async def rerank(
        self,
        *,
        model_id: str,
        request_id: str,
        query: str,
        documents: list[str],
        timeout: float = 60,
        cancel: asyncio.Event | None = None,
    ) -> list[float]:
        return await self._local.rerank(
            model_id=model_id,
            request_id=request_id,
            query=query,
            documents=documents,
            timeout=timeout,
            cancel=cancel,
        )
