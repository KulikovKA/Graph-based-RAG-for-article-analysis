"""Pinned Tev1 relation classification for Analyst feature/document pairs."""

from __future__ import annotations

import asyncio
import json
import math
import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx

from app.domain.inference import (
    InferenceCancelled,
    InferenceProtocolError,
    InferenceTimeout,
    InferenceUnavailable,
)
from app.domain.planner import IdeaV1
from app.services.evidence_pack import EvidencePack

RELATION_LABELS = ("full", "partial", "conflicting", "uncertain", "none")
RUBRIC = {
    "full": "Evidence directly and sufficiently supports all material aspects of the feature.",
    "partial": (
        "Evidence supports some material aspects of the feature, but not all required aspects; "
        "there is no material contradiction."
    ),
    "conflicting": "Evidence materially contradicts one or more required aspects of the feature.",
    "uncertain": (
        "Evidence is relevant, but is ambiguous or insufficient to decide whether the feature is "
        "supported or contradicted."
    ),
    "none": (
        "Evidence is unrelated to the feature and does not address its material properties; "
        "relevant evidence without a clear result is uncertain."
    ),
}


@dataclass(frozen=True)
class RelationDecision:
    feature_id: UUID
    document_id: UUID
    relation: str
    probabilities: dict[str, float]
    confidence: float


class RelationClassifier:
    def __init__(self, client: httpx.AsyncClient, *, model_id: str, digest: str) -> None:
        self.client = client
        self.model_id = model_id
        self.digest = digest
        self.last_latencies_ms: list[float] = []

    async def classify(
        self,
        *,
        idea: IdeaV1,
        pack: EvidencePack,
        request_id: str,
        timeout: float,
        cancel: asyncio.Event | None = None,
    ) -> dict[tuple[UUID, UUID], RelationDecision]:
        groups: dict[UUID, list[Any]] = {}
        for item in pack.items:
            groups.setdefault(item.document_id, []).append(item)
        result: dict[tuple[UUID, UUID], RelationDecision] = {}
        self.last_latencies_ms = []
        deadline = time.monotonic() + timeout
        for feature in idea.features:
            for document_id, items in groups.items():
                if cancel is not None and cancel.is_set():
                    raise InferenceCancelled("relation classification cancelled")
                # SystemOne uses these opaque IDs as state keys; source IDs are
                # stable across retries and match the frozen benchmark contract.
                state_ids = ",".join(item.external_id for item in items)
                state = {
                    "feature_id": state_ids,
                    "feature_text": feature.text,
                    "feature_language": idea.language,
                    "evidence_id": state_ids,
                    "evidence_text": "\n".join(item.quoted_span for item in items),
                }
                if len(json.dumps(state, ensure_ascii=False).encode("utf-8")) > 6000:
                    raise InferenceProtocolError("relation classifier state exceeds size limit")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise InferenceTimeout("relation classifier deadline exceeded")
                payload = {
                    "model": self.model_id,
                    "state": state,
                    "questions": {
                        "relation": {
                            "type": "choice",
                            "instructions": (
                                "How does this evidence relate to the technical feature?"
                            ),
                            "criteria": RUBRIC,
                        }
                    },
                    "keep_alive": "30m",
                }
                try:
                    started = time.perf_counter()
                    response = await self.client.post(
                        "/v1/systemone",
                        json=payload,
                        timeout=remaining,
                        headers={"X-Request-ID": request_id},
                    )
                    response.raise_for_status()
                    body = response.json()
                    self.last_latencies_ms.append((time.perf_counter() - started) * 1000)
                except httpx.TimeoutException as exc:
                    raise InferenceTimeout("relation classifier timed out") from exc
                except (httpx.HTTPError, ValueError) as exc:
                    raise InferenceUnavailable("relation classifier unavailable") from exc
                decision = self._validate(body)
                result[(feature.id, document_id)] = RelationDecision(
                    feature.id, document_id, decision[0], decision[1], decision[2]
                )
        return result

    def _validate(self, body: Any) -> tuple[str, dict[str, float], float]:
        if not isinstance(body, dict) or body.get("model") != self.model_id:
            raise InferenceProtocolError("relation classifier response model mismatch")
        answers = body.get("answers")
        answer = answers.get("relation") if isinstance(answers, dict) else None
        if not isinstance(answer, dict) or answer.get("type") != "choice":
            raise InferenceProtocolError("relation classifier response schema invalid")
        label = answer.get("choice")
        if label not in RELATION_LABELS:
            raise InferenceProtocolError("relation classifier returned invalid label")
        raw = answer.get("probabilities")
        if not isinstance(raw, dict) or set(raw) != set(RELATION_LABELS):
            raise InferenceProtocolError("relation classifier probabilities malformed")
        probabilities: dict[str, float] = {}
        for key, value in raw.items():
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise InferenceProtocolError("relation classifier probability invalid")
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise InferenceProtocolError("relation classifier probability invalid")
            probabilities[key] = float(value)
        if abs(sum(probabilities.values()) - 1.0) > 0.01:
            raise InferenceProtocolError("relation classifier probabilities not normalized")
        if label != max(RELATION_LABELS, key=probabilities.__getitem__):
            raise InferenceProtocolError("relation classifier choice contradicts probabilities")
        confidence = answer.get("confidence")
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, int | float)
            or not math.isfinite(confidence)
            or not 0 <= confidence <= 1
        ):
            raise InferenceProtocolError("relation classifier confidence invalid")
        return str(label), probabilities, float(confidence)
