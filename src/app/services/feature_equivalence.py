"""Dedicated Tev1 SystemOne contract for conservative technical-feature equivalence."""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from app.domain.inference import (
    InferenceProtocolError,
    InferenceTimeout,
    InferenceUnavailable,
)

FEATURE_EQUIVALENCE_CONTRACT = "feature-equivalence-v1"
EQUIVALENCE_LABELS = ("SAME", "DIFFERENT", "UNCERTAIN")
EQUIVALENCE_CRITERIA = {
    "SAME": (
        "Both phrases name the same technical feature, property, or entity in context; "
        "differences are wording, synonymy, spelling, or immaterial qualification only."
    ),
    "DIFFERENT": (
        "The technical concepts differ. Choose DIFFERENT when analyte, material, polarity, "
        "process, operating condition, property, mechanism, or breadth differs. Examples: "
        "NO2 sensitivity vs NH3 sensitivity; n-type vs p-type; gas sensing vs NO2 sensing; "
        "room-temperature operation vs room-temperature synthesis."
    ),
    "UNCERTAIN": (
        "Context is insufficient or equivalence is ambiguous. "
        "False merge is worse than a missed merge."
    ),
}


@dataclass(frozen=True)
class FeatureEquivalenceDecision:
    decision: Literal["SAME", "DIFFERENT", "UNCERTAIN"]
    probabilities: dict[str, float]
    confidence: float
    latency_ms: float


class FeatureEquivalenceClassifier:
    """Uses the pinned relation-classifier model through an independent contract."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        model_id: str,
        digest: str,
        max_state_bytes: int = 6000,
        context_chars: int = 800,
    ) -> None:
        if not model_id or not digest or max_state_bytes < 256 or context_chars < 0:
            raise ValueError("invalid feature equivalence classifier configuration")
        self.client = client
        self.model_id = model_id
        self.digest = digest
        self.max_state_bytes = max_state_bytes
        self.context_chars = context_chars

    async def classify(
        self,
        *,
        feature_a: str,
        feature_b: str,
        context_a: str = "",
        context_b: str = "",
        request_id: str,
        timeout: float = 120,
    ) -> FeatureEquivalenceDecision:
        if not feature_a.strip() or not feature_b.strip() or feature_a == feature_b:
            raise ValueError("feature pair must contain two distinct nonempty values")
        state = {
            "contract_version": FEATURE_EQUIVALENCE_CONTRACT,
            "feature_a": feature_a[:512],
            "feature_b": feature_b[:512],
            "source_context_a": context_a[: self.context_chars],
            "source_context_b": context_b[: self.context_chars],
        }
        if len(json.dumps(state, ensure_ascii=False).encode("utf-8")) > self.max_state_bytes:
            raise InferenceProtocolError("feature equivalence state exceeds size limit")
        payload = {
            "model": self.model_id,
            "state": state,
            "questions": {
                "equivalence": {
                    "type": "choice",
                    "instructions": (
                        "Are these two technical features equivalent in their cited source "
                        "contexts? Prefer UNCERTAIN whenever equivalence is ambiguous. "
                        "A semantic similarity score alone is not evidence of equivalence."
                    ),
                    "criteria": EQUIVALENCE_CRITERIA,
                }
            },
            "keep_alive": "30m",
        }
        started = time.perf_counter()
        try:
            response = await self.client.post(
                "/v1/systemone",
                json=payload,
                timeout=timeout,
                headers={"X-Request-ID": request_id},
            )
            response.raise_for_status()
            body = response.json()
        except httpx.TimeoutException as exc:
            raise InferenceTimeout("feature equivalence classifier timed out") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise InferenceUnavailable("feature equivalence classifier unavailable") from exc
        latency_ms = (time.perf_counter() - started) * 1000
        decision, probabilities, confidence = self._validate(body)
        return FeatureEquivalenceDecision(decision, probabilities, confidence, latency_ms)

    def _validate(
        self, body: Any
    ) -> tuple[Literal["SAME", "DIFFERENT", "UNCERTAIN"], dict[str, float], float]:
        if not isinstance(body, dict) or body.get("model") != self.model_id:
            raise InferenceProtocolError("feature equivalence response model mismatch")
        answers = body.get("answers")
        answer = answers.get("equivalence") if isinstance(answers, dict) else None
        if not isinstance(answer, dict) or answer.get("type") != "choice":
            raise InferenceProtocolError("feature equivalence response schema invalid")
        label = answer.get("choice")
        if label not in EQUIVALENCE_LABELS:
            raise InferenceProtocolError("feature equivalence response label invalid")
        raw_probabilities = answer.get("probabilities")
        if not isinstance(raw_probabilities, dict) or set(raw_probabilities) != set(
            EQUIVALENCE_LABELS
        ):
            raise InferenceProtocolError("feature equivalence probabilities malformed")
        probabilities: dict[str, float] = {}
        for key in EQUIVALENCE_LABELS:
            value = raw_probabilities[key]
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise InferenceProtocolError("feature equivalence probability invalid")
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise InferenceProtocolError("feature equivalence probability invalid")
            probabilities[key] = float(value)
        if abs(sum(probabilities.values()) - 1.0) > 0.01:
            raise InferenceProtocolError("feature equivalence probabilities not normalized")
        maximum = max(EQUIVALENCE_LABELS, key=probabilities.__getitem__)
        if label != maximum:
            raise InferenceProtocolError("feature equivalence choice contradicts probabilities")
        confidence = answer.get("confidence")
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, int | float)
            or not math.isfinite(confidence)
            or not 0 <= confidence <= 1
        ):
            raise InferenceProtocolError("feature equivalence confidence invalid")
        return label, probabilities, float(confidence)
