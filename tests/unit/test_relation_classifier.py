"""Protocol and privacy guards for the dedicated relation classifier."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import httpx
import pytest

from app.domain.inference import InferenceProtocolError, InferenceTimeout
from app.domain.planner import FeatureV1, IdeaV1
from app.services.evidence_pack import EvidencePack, EvidencePackItem
from app.services.relation_classifier import RELATION_LABELS, RelationClassifier


def response(*, label: str = "partial", probabilities: dict[str, float] | None = None):
    probs = probabilities or {name: float(name == label) for name in RELATION_LABELS}
    return {
        "model": "tev1:4b",
        "answers": {
            "relation": {
                "type": "choice",
                "choice": label,
                "probabilities": probs,
                "confidence": 0.9,
            }
        },
    }


def classifier() -> RelationClassifier:
    return RelationClassifier(
        None,
        model_id="tev1:4b",
        digest="cef45ef93cf6df8bf32bdd689b0a8fd01f88ae9034d33ce890c54f77e4cd981e",
    )  # type: ignore[arg-type]


def test_valid_label_and_probabilities_are_accepted() -> None:
    assert classifier()._validate(response())[0] == "partial"


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (response(label="fallback"), "invalid label"),
        (response(probabilities={"full": 0.2}), "probabilities malformed"),
        (response(probabilities={name: 0.1 for name in RELATION_LABELS}), "not normalized"),
        (
            response(
                label="partial",
                probabilities={
                    "full": 1.0,
                    "partial": 0.0,
                    "conflicting": 0.0,
                    "uncertain": 0.0,
                    "none": 0.0,
                },
            ),
            "contradicts probabilities",
        ),
    ],
)
def test_invalid_label_and_malformed_probabilities_are_rejected(body, message) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(InferenceProtocolError, match=message):
        classifier()._validate(body)


def test_non_finite_probability_is_rejected() -> None:
    probs = {name: 0.0 for name in RELATION_LABELS}
    probs["partial"] = float("nan")
    with pytest.raises(InferenceProtocolError, match="probability invalid"):
        classifier()._validate(response(probabilities=probs))


def test_classifier_timeout_is_typed() -> None:
    class TimeoutClient:
        async def post(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise httpx.ReadTimeout("backend timeout")

    feature_id, document_id, evidence_id = uuid4(), uuid4(), uuid4()
    idea = IdeaV1(features=[FeatureV1(id=feature_id, text="feature")], language="en")
    item = EvidencePackItem(
        evidence_id=evidence_id,
        document_id=document_id,
        revision_id=uuid4(),
        chunk_id=uuid4(),
        source="test",
        external_id="test-doc",
        canonical_url="https://example.invalid/test",
        title="test",
        section="test",
        language="en",
        span_start=0,
        span_end=5,
        quoted_span="quote",
        retrieval_score=1.0,
        rerank_score=1.0,
    )
    pack = EvidencePack(items=(item,), token_count=5, token_budget=100)
    with pytest.raises(InferenceTimeout):
        asyncio.run(classifier_with(TimeoutClient()).classify(
            idea=idea, pack=pack, request_id="test", timeout=1
        ))


def classifier_with(client: object) -> RelationClassifier:
    return RelationClassifier(
        client,  # type: ignore[arg-type]
        model_id="tev1:4b",
        digest="cef45ef93cf6df8bf32bdd689b0a8fd01f88ae9034d33ce890c54f77e4cd981e",
    )
