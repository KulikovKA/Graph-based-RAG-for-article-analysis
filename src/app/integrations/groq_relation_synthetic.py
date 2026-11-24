"""Синтетический контракт классификации; к пользовательскому worker не подключается."""

import asyncio
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from app.domain.inference import InferenceProtocolError, InferenceProvider
from app.services.relation_classifier import RELATION_LABELS, RUBRIC

PROMPT_VERSION = "relation_classifier_synthetic_v1"
RelationLabel = Literal["full", "partial", "conflicting", "uncertain", "none"]


class SyntheticRelationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    relation: RelationLabel

    @field_validator("relation")
    @classmethod
    def check_relation(cls, value: RelationLabel) -> RelationLabel:
        if value not in RELATION_LABELS:
            raise ValueError("invalid relation label")
        return value


async def classify_synthetic_relation(
    provider: InferenceProvider,
    *,
    model_id: str,
    request_id: str,
    timeout: float,
    cancel: asyncio.Event | None = None,
) -> SyntheticRelationResult:
    """Использовать только встроенный искусственный пример, без данных пользователя."""
    prompt = (
        "Classify the relation of the synthetic evidence to the feature. "
        "Return a JSON object with the single key relation. "
        f"Allowed labels and criteria: {json.dumps(RUBRIC, sort_keys=True)}. "
        "Feature: a red test cube. Evidence: a red test cube."
    )
    result = await provider.complete_json(
        model_id=model_id,
        prompt_version=PROMPT_VERSION,
        request_id=request_id,
        prompt=prompt,
        timeout=timeout,
        schema=SyntheticRelationResult.model_json_schema(),
        max_output_tokens=512,
        cancel=cancel,
    )
    try:
        return SyntheticRelationResult.model_validate(result.value)
    except ValidationError:
        raise InferenceProtocolError("invalid synthetic relation result") from None
