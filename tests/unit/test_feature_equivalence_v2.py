from __future__ import annotations

import json

import pytest

from app.services.feature_equivalence import FEATURE_EQUIVALENCE_CONTRACT
from app.services.feature_equivalence_v2 import (
    CONTRACT_3_CRITERIA,
    CONTRACT_3_LABELS,
    CONTRACT_5_CRITERIA,
    CONTRACT_5_LABELS,
    CONTRACT_VERSION,
    FeatureEquivalenceClassifierV2,
    load_decision_cache,
    merge_eligible,
    safety_veto,
)


def response(model: str, labels: tuple[str, ...], decision: str = "SAME") -> dict:
    probabilities = {
        label: (0.9 if label == decision else 0.1 / (len(labels) - 1)) for label in labels
    }
    return {
        "model": model,
        "answers": {
            "equivalence": {
                "type": "choice",
                "choice": decision,
                "probabilities": probabilities,
                "confidence": 0.8,
            }
        },
    }


def classifier() -> FeatureEquivalenceClassifierV2:
    return FeatureEquivalenceClassifierV2(None, model_id="tev1:4b", digest="pinned")  # type: ignore[arg-type]


def test_contract_schemas_and_versions_are_separate() -> None:
    assert CONTRACT_3_LABELS == ("SAME", "DIFFERENT", "UNCERTAIN")
    assert CONTRACT_5_LABELS == ("SAME", "RELATED", "BROADER_NARROWER", "DIFFERENT", "UNCERTAIN")
    assert CONTRACT_VERSION == "feature-equivalence-v2"
    assert FEATURE_EQUIVALENCE_CONTRACT == "feature-equivalence-v1"


def test_same_definition_is_strict_and_related_is_not_merge() -> None:
    assert (
        "without losing technical meaning, scope, polarity, analyte" in CONTRACT_5_CRITERIA["SAME"]
    )
    assert "broader category" in CONTRACT_5_CRITERIA["BROADER_NARROWER"]
    assert "related concepts" in CONTRACT_3_CRITERIA["DIFFERENT"]
    assert not merge_eligible(
        decision="RELATED",
        same_probability=1.0,
        threshold=0.7,
        feature_a="graphene",
        feature_b="atomic thickness",
    )[0]


@pytest.mark.parametrize(
    "contract,labels", [("3-class", CONTRACT_3_LABELS), ("5-class", CONTRACT_5_LABELS)]
)
def test_contract_response_schema(contract: str, labels: tuple[str, ...]) -> None:
    assert classifier()._validate(response("tev1:4b", labels), labels)[0] == "SAME"


def test_all_non_same_labels_do_not_merge_and_different_is_cannot_link() -> None:
    for label in ("RELATED", "BROADER_NARROWER", "DIFFERENT", "UNCERTAIN"):
        assert not merge_eligible(
            decision=label,
            same_probability=1.0,
            threshold=0.7,
            feature_a="gas sensing",
            feature_b="NO2 sensing",
        )[0]


def test_only_one_probability_threshold_is_applied() -> None:
    assert merge_eligible(
        decision="SAME",
        same_probability=0.8,
        threshold=0.8,
        feature_a="transparency",
        feature_b="transparent",
    ) == (True, None)
    assert not merge_eligible(
        decision="SAME",
        same_probability=0.799,
        threshold=0.8,
        feature_a="transparency",
        feature_b="transparent",
    )[0]
    with pytest.raises(ValueError):
        merge_eligible(
            decision="SAME", same_probability=0.99, threshold=1.1, feature_a="a", feature_b="b"
        )


@pytest.mark.parametrize(
    "left,right",
    [
        ("n-type semiconducting behavior", "p-type semiconducting behavior"),
        ("NO2 sensitivity", "NH3 sensitivity"),
        ("high selectivity", "low selectivity"),
        ("increase in resistance", "decrease in resistance"),
        ("with external heating", "without external heating"),
        ("oxidation process", "reduction process"),
        ("oxidizing reaction process", "reduction process"),
        ("positive polarity", "negative polarity"),
    ],
)
def test_safety_veto_prevents_contrast_merges(left: str, right: str) -> None:
    assert safety_veto(left, right)
    accepted, reason = merge_eligible(
        decision="SAME", same_probability=0.999, threshold=0.7, feature_a=left, feature_b=right
    )
    assert not accepted and reason


def test_safety_veto_is_not_an_aggressive_same_token_rule() -> None:
    assert safety_veto("NO2 sensing", "NO2 sensitivity") is None
    assert safety_veto("high optical transparency", "optical transparency") is None
    assert safety_veto("high sensitivity", "low selectivity") is None
    assert (
        safety_veto(
            "reliable sensing performance with a bending strain of less than 1.4",
            "robust flexibility without a performance decrease",
        )
        is None
    )


def test_probability_response_must_match_contract_schema() -> None:
    body = response("tev1:4b", CONTRACT_5_LABELS)
    body["answers"]["equivalence"]["probabilities"].pop("RELATED")
    with pytest.raises(Exception, match="probabilities malformed"):
        classifier()._validate(body, CONTRACT_5_LABELS)


def test_v2_decision_records_use_separate_version() -> None:
    item = {"contract_version": CONTRACT_VERSION, "probabilities": {"SAME": 1.0}}
    assert json.loads(json.dumps(item))["contract_version"] != FEATURE_EQUIVALENCE_CONTRACT


def test_calibration_rerun_reuses_existing_pair_decision(tmp_path) -> None:
    path = tmp_path / "decisions.jsonl"
    item = {
        "contract": "5-class",
        "feature_a": "low selectivity",
        "feature_b": "poor selectivity",
        "decision": "SAME",
        "probabilities": {"SAME": 0.99},
    }
    path.write_text(json.dumps(item) + "\n", encoding="utf-8")
    previous = load_decision_cache(path)
    assert previous[("5-class", "low selectivity", "poor selectivity")] == item
    assert load_decision_cache(path) == previous
