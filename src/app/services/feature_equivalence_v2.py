"""Strict, versioned feature-equivalence contract for GRAPH-002 calibration."""

from __future__ import annotations

import json
import math
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import httpx

from app.domain.inference import (
    InferenceProtocolError,
    InferenceTimeout,
    InferenceUnavailable,
)

CONTRACT_VERSION = "feature-equivalence-v2"
CONTRACT_3_LABELS = ("SAME", "DIFFERENT", "UNCERTAIN")
CONTRACT_5_LABELS = ("SAME", "RELATED", "BROADER_NARROWER", "DIFFERENT", "UNCERTAIN")
STRICT_SAME_DEFINITION = (
    "These two expressions can safely be represented by one exact canonical "
    "TechnicalFeature in the knowledge graph without losing technical meaning, scope, "
    "polarity, analyte, material, mechanism, process, operating condition, or hierarchy level."
)
CONTRACT_5_CRITERIA = {
    "SAME": STRICT_SAME_DEFINITION,
    "RELATED": (
        "Same technical object, topic, or phenomenon, but distinct concepts or properties; "
        "includes a definition and the thing it defines, or a property of an object."
    ),
    "BROADER_NARROWER": (
        "One concept is a broader category or narrower specialization of the other."
    ),
    "DIFFERENT": (
        "Distinct concepts without a safe equivalence. Preserve different analytes, polarity, "
        "direction, property, process, condition, mechanism, and technical scope."
    ),
    "UNCERTAIN": "The available wording and short contexts do not support a safe decision.",
}
CONTRACT_3_CRITERIA = {
    "SAME": STRICT_SAME_DEFINITION,
    "DIFFERENT": (
        "Use for all non-equivalent pairs, including related concepts, broader/narrower "
        "concepts, different analytes, polarity, direction, property, process, conditions, "
        "mechanism, and technical scope."
    ),
    "UNCERTAIN": "The available wording and short contexts do not support a safe decision.",
}
CONTRACT_INSTRUCTIONS = (
    "Judge exact technical-concept equivalence, not topical relatedness. DO NOT choose SAME "
    "merely because both describe graphene, occur in one scientific domain, one defines the "
    "other, one is a property of the other, they are causally related, or embeddings are close. "
    "Use only the supplied phrases and short symmetric source contexts. False merges are worse "
    "than missed merges."
)

_DIRECTION_CONTRASTS = (
    (re.compile(r"\bhigh\b", re.I), re.compile(r"\blow\b", re.I)),
    (re.compile(r"\bincrease(?:d|s)?\b", re.I), re.compile(r"\bdecrease(?:d|s)?\b", re.I)),
    (re.compile(r"\bwith\b", re.I), re.compile(r"\bwithout\b", re.I)),
    (re.compile(r"\bpositive\b", re.I), re.compile(r"\bnegative\b", re.I)),
)


@dataclass(frozen=True)
class EquivalenceV2Decision:
    decision: str
    probabilities: dict[str, float]
    confidence: float
    latency_ms: float


def safety_veto(feature_a: str, feature_b: str) -> str | None:
    """Return a review reason for obvious polarity/analyte/direction contrasts."""
    n_type = re.compile(r"\bn\s*[- ]?type\b", re.I)
    p_type = re.compile(r"\bp\s*[- ]?type\b", re.I)
    if (n_type.search(feature_a) and p_type.search(feature_b)) or (
        p_type.search(feature_a) and n_type.search(feature_b)
    ):
        return "opposite carrier polarity (n-type vs p-type)"
    oxidation = re.compile(r"\boxid(?:ation|iz(?:e|ed|ing))\b", re.I)
    reduction = re.compile(r"\breduction\b", re.I)
    if (oxidation.search(feature_a) and reduction.search(feature_b)) or (
        reduction.search(feature_a) and oxidation.search(feature_b)
    ):
        return "opposing oxidation/reduction processes"
    for left, right in _DIRECTION_CONTRASTS:
        if (left.search(feature_a) and right.search(feature_b)) or (
            right.search(feature_a) and left.search(feature_b)
        ):
            residue_a = _without_markers(feature_a, (left, right))
            residue_b = _without_markers(feature_b, (left, right))
            if residue_a and residue_a == residue_b:
                return "contradictory technical qualifier"
    # Keep analyte checks scoped to named chemical tokens, not arbitrary substrings.
    no2 = re.compile(r"\bno\s*2\b", re.I)
    nh3 = re.compile(r"\bnh\s*3\b", re.I)
    if (no2.search(feature_a) and nh3.search(feature_b)) or (
        nh3.search(feature_a) and no2.search(feature_b)
    ):
        return "different analytes (NO2 vs NH3)"
    return None


def _without_markers(value: str, markers: tuple[re.Pattern[str], re.Pattern[str]]) -> str:
    value = markers[0].sub(" ", value)
    value = markers[1].sub(" ", value)
    return re.sub(r"\W+", " ", value.casefold()).strip()


def merge_eligible(
    *, decision: str, same_probability: float, threshold: float, feature_a: str, feature_b: str
) -> tuple[bool, str | None]:
    """One threshold policy: SAME label plus SAME probability, then safety veto."""
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between zero and one")
    if decision != "SAME" or same_probability < threshold:
        return False, None
    reason = safety_veto(feature_a, feature_b)
    return reason is None, reason


def load_decision_cache(path: Path) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Load versioned pair results so an interrupted benchmark can resume idempotently."""
    if not path.exists():
        return {}
    output: dict[tuple[str, str, str], dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        key = (item["contract"], item["feature_a"], item["feature_b"])
        output[key] = item
    return output


class FeatureEquivalenceClassifierV2:
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
        contract: Literal["3-class", "5-class"],
        request_id: str,
        timeout: float = 120,
    ) -> EquivalenceV2Decision:
        if not feature_a.strip() or not feature_b.strip() or feature_a == feature_b:
            raise ValueError("feature pair must contain two distinct nonempty values")
        labels = CONTRACT_3_LABELS if contract == "3-class" else CONTRACT_5_LABELS
        criteria = CONTRACT_3_CRITERIA if contract == "3-class" else CONTRACT_5_CRITERIA
        state = {
            "contract_version": CONTRACT_VERSION,
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
                    "instructions": CONTRACT_INSTRUCTIONS,
                    "criteria": criteria,
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
            raise InferenceTimeout("feature equivalence v2 classifier timed out") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise InferenceUnavailable("feature equivalence v2 classifier unavailable") from exc
        elapsed = (time.perf_counter() - started) * 1000
        decision, probabilities, confidence = self._validate(body, labels)
        return EquivalenceV2Decision(decision, probabilities, confidence, elapsed)

    def _validate(self, body: Any, labels: tuple[str, ...]) -> tuple[str, dict[str, float], float]:
        if not isinstance(body, dict) or body.get("model") != self.model_id:
            raise InferenceProtocolError("feature equivalence v2 response model mismatch")
        answers = body.get("answers")
        answer = answers.get("equivalence") if isinstance(answers, dict) else None
        if not isinstance(answer, dict) or answer.get("type") != "choice":
            raise InferenceProtocolError("feature equivalence v2 response schema invalid")
        label = answer.get("choice")
        if label not in labels:
            raise InferenceProtocolError("feature equivalence v2 response label invalid")
        raw = answer.get("probabilities")
        if not isinstance(raw, dict) or set(raw) != set(labels):
            raise InferenceProtocolError("feature equivalence v2 probabilities malformed")
        probabilities: dict[str, float] = {}
        for key in labels:
            value = raw[key]
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise InferenceProtocolError("feature equivalence v2 probability invalid")
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise InferenceProtocolError("feature equivalence v2 probability invalid")
            probabilities[key] = float(value)
        if abs(sum(probabilities.values()) - 1.0) > 0.01:
            raise InferenceProtocolError("feature equivalence v2 probabilities not normalized")
        if label != max(labels, key=probabilities.__getitem__):
            raise InferenceProtocolError("feature equivalence v2 choice contradicts probabilities")
        confidence = answer.get("confidence")
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, int | float)
            or not math.isfinite(confidence)
            or not 0 <= confidence <= 1
        ):
            raise InferenceProtocolError("feature equivalence v2 confidence invalid")
        return str(label), probabilities, float(confidence)
