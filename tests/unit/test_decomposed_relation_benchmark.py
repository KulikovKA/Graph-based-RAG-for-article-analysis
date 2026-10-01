"""Deterministic relation composition rules for the rejected experiment."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "decomposed_relation_benchmark", ROOT / "scripts/decomposed_relation_benchmark.py"
)
assert SPEC is not None and SPEC.loader is not None
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)


def decisions(**changes: str) -> dict[str, str]:
    value = {
        "contradiction": "no",
        "supports_all": "no",
        "supports_some": "no",
        "relevant": "no",
    }
    return value | changes


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ({"supports_all": "yes", "supports_some": "yes", "relevant": "yes"}, "full"),
        ({"supports_some": "yes", "relevant": "yes"}, "partial"),
        ({"relevant": "yes"}, "uncertain"),
        ({}, "none"),
        ({"contradiction": "yes"}, "conflicting"),
    ],
)
def test_deterministic_decision_precedence(values: dict[str, str], expected: str) -> None:
    assert benchmark.assemble(decisions(**values)) == expected


@pytest.mark.parametrize(
    "values",
    [
        {"contradiction": "yes", "supports_all": "yes", "supports_some": "yes"},
        {"contradiction": "yes", "supports_some": "yes"},
        {"supports_all": "yes", "supports_some": "no"},
        {"supports_some": "yes", "relevant": "no"},
    ],
)
def test_impossible_combinations_are_rejected(values: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="inconsistent"):
        benchmark.assemble(decisions(**values))
