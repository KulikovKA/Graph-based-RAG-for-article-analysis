"""Загрузка изолированного профиля и порт только для фиксированной синтетики."""

from __future__ import annotations

import asyncio
import json
import math
import time
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import jsonschema  # type: ignore[import-untyped]
import yaml

from app.domain.inference import InferenceConfigurationError
from app.domain.synthetic_guard import SYNTHETIC_EXCERPTS, SYNTHETIC_IDEA
from app.integrations.groq import (
    GroqPrice,
    GroqProvider,
    GroqProviderFactory,
    GroqRole,
    LocalInferencePort,
)
from app.integrations.groq_relation_synthetic import SyntheticRelationResult

MODEL = "openai/gpt-oss-20b"
SYSTEM = "Classify the synthetic relation. Return only the relation label as JSON."


class JsonSchemaValidator:
    def check_schema(self, schema: dict[str, Any]) -> None:
        jsonschema.Draft202012Validator.check_schema(schema)

    def validate(self, value: dict[str, Any], schema: dict[str, Any]) -> None:
        jsonschema.Draft202012Validator(schema).validate(value)


def load_synthetic_profile(path: Path) -> tuple[dict[str, GroqRole], dict[str, GroqPrice]]:
    """Принимает только фиксированный отключённый профиль с проверенным тарифом."""
    try:
        profile = yaml.safe_load(path.read_text(encoding="utf-8"))
        if profile["enabled"] is not False:
            raise ValueError
        roles = {}
        versions = {
            "planner": "planner_v3",
            "analyst": "analyst_v4",
            "narrative": "narrative_synthetic_v1",
            "relation_classifier": "relation_classifier_synthetic_v1",
        }
        for name, version in versions.items():
            row = profile["roles"][name]
            if (
                row["model_id"] != MODEL
                or row["capability"] != "json_schema"
                or row["prompt_version"] != version
            ):
                raise ValueError
            roles[name] = GroqRole(
                model_id=MODEL,
                prompt_version=version,
                capability="json_schema",
                timeout=min(float(row["timeout_seconds"]), 30),
                max_output_tokens=min(int(row["max_output_tokens"]), 512),
                reasoning_efforts=tuple(row.get("reasoning_efforts", [])),
            )
        price = profile["prices"][MODEL]
        if (
            Decimal(price["input_per_million"]) != Decimal("0.075")
            or Decimal(price["output_per_million"]) != Decimal("0.30")
            or price["currency"] != "USD"
            or price["source"] != "https://console.groq.com/docs/models"
            or price["version"] != "groq-models-2026-11-24"
        ):
            raise ValueError
        return roles, {
            MODEL: GroqPrice(
                Decimal("0.075"), Decimal("0.30"), "USD", price["source"], price["version"]
            )
        }
    except (OSError, KeyError, TypeError, ValueError, yaml.YAMLError, ArithmeticError):
        raise InferenceConfigurationError("invalid synthetic profile") from None


@dataclass(frozen=True)
class SyntheticRuntime:
    provider: GroqProvider
    roles: dict[str, GroqRole]
    prices: dict[str, GroqPrice]


def create_synthetic_runtime(
    client: httpx.AsyncClient,
    *,
    api_key: str,
    path: Path,
    local: LocalInferencePort,
    max_attempts: int = 1,
) -> SyntheticRuntime:
    roles, prices = load_synthetic_profile(path)
    provider = GroqProviderFactory(
        client,
        api_key=api_key,
        roles=roles,
        prices=prices,
        validator=JsonSchemaValidator(),
        local=local,
        max_parallel=1,
        max_attempts=max_attempts,
    ).for_run(max_requests=4, max_tokens=50000, max_cost=Decimal("0.02"))
    return SyntheticRuntime(provider=provider, roles=roles, prices=prices)


def synthetic_provider(
    client: httpx.AsyncClient,
    *,
    api_key: str,
    path: Path,
    local: LocalInferencePort,
    max_attempts: int = 1,
) -> GroqProvider:
    return create_synthetic_runtime(
        client, api_key=api_key, path=path, local=local, max_attempts=max_attempts
    ).provider


class SyntheticGuardPort:
    """Не передаёт данные из Guard, кроме заранее заданного тестового примера."""

    def __init__(self, provider: GroqProvider, *, deadline: float, cancel: asyncio.Event) -> None:
        if not math.isfinite(deadline) or not isinstance(cancel, asyncio.Event):
            raise InferenceConfigurationError("invalid synthetic run")
        self._provider = provider
        self._deadline = deadline
        self._cancel = cancel

    async def generate(
        self, *, system: str, data: str, timeout: float, cancel: asyncio.Event
    ) -> dict[str, Any]:
        expected = {"idea": SYNTHETIC_IDEA, "excerpts": list(SYNTHETIC_EXCERPTS)}
        try:
            if cancel is not self._cancel or json.loads(data) != expected:
                raise ValueError
        except (TypeError, ValueError):
            raise InferenceConfigurationError("synthetic context required") from None
        result = await self._provider.complete_guarded_json(
            system=SYSTEM,
            data=json.dumps(expected),
            model_id=MODEL,
            prompt_version="relation_classifier_synthetic_v1",
            request_id="synthetic",
            timeout=min(timeout, self._deadline - time.monotonic()),
            schema=SyntheticRelationResult.model_json_schema(),
            max_output_tokens=512,
            cancel=cancel,
        )
        return SyntheticRelationResult.model_validate(result.value).model_dump()
