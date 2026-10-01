"""Contract tests for the isolated Tev1 benchmark harness."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "tev1_relation_benchmark", ROOT / "scripts/tev1_relation_benchmark.py"
)
assert SPEC is not None and SPEC.loader is not None
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)


def valid_response() -> dict[str, object]:
    return {
        "model": benchmark.MODEL,
        "answers": {
            "relation": {
                "type": "choice",
                "choice": "partial",
                "probabilities": {
                    "full": 0.1,
                    "partial": 0.7,
                    "conflicting": 0.05,
                    "uncertain": 0.1,
                    "none": 0.05,
                },
                "confidence": 0.3,
            }
        },
        "usage": {"input_tokens": 123},
    }


def test_compact_state_preserves_russian_feature_and_exact_evidence() -> None:
    feature = "корпус не пропускает воду"
    quote = "Испытание показало, что корпус пропускает воду."
    state = benchmark.compact_state(
        {"case_id": "AN-08", "feature": feature, "quote": quote, "language": "ru"}
    )
    assert state["feature_text"] == feature
    assert state["evidence_text"] == quote
    assert state["feature_language"] == "ru"
    assert set(state) == {
        "feature_id",
        "feature_text",
        "feature_language",
        "evidence_id",
        "evidence_text",
    }


def test_compact_state_supports_russian_feature_with_english_evidence() -> None:
    state = benchmark.compact_state(
        {
            "case_id": "RU-EN",
            "feature": "датчик обнаруживает утечку газа",
            "quote": "The sensor detects gas leakage.",
            "language": "ru",
        }
    )
    assert state["feature_language"] == "ru"
    assert state["evidence_text"] == "The sensor detects gas leakage."


def test_compact_state_deterministically_rejects_oversized_quote() -> None:
    case = {
        "case_id": "AN-X",
        "feature": "feature",
        "quote": "q" * 7000,
        "language": "en",
    }
    with pytest.raises(ValueError, match="size guard"):
        benchmark.compact_state(case)


def test_valid_systemone_choice_captures_all_probabilities_and_usage() -> None:
    label, probabilities, confidence, usage = benchmark.validate_answer(valid_response())
    assert label == "partial"
    assert set(probabilities) == set(benchmark.LABELS)
    assert probabilities["partial"] == 0.7
    assert confidence == 0.3
    assert usage["input_tokens"] == 123


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda data: data["answers"]["relation"].update(choice="other"), "invalid_label"),
        (
            lambda data: data["answers"]["relation"].update(choice="full"),
            "choice_probability_mismatch",
        ),
        (
            lambda data: data["answers"]["relation"]["probabilities"].update(partial="high"),
            "invalid_probability_value",
        ),
        (
            lambda data: data["answers"]["relation"]["probabilities"].pop("none"),
            "invalid_probabilities_schema",
        ),
        (
            lambda data: data["answers"]["relation"].update(confidence=1.2),
            "invalid_confidence",
        ),
    ],
)
def test_rejects_unknown_labels_and_malformed_probability_data(mutate, message) -> None:  # type: ignore[no-untyped-def]
    response = valid_response()
    mutate(response)
    with pytest.raises(ValueError, match=message):
        benchmark.validate_answer(response)
