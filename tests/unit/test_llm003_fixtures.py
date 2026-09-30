"""Sanity checks for the deterministic, human-labeled LLM-003 fixtures."""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "eval/llm003"


def load(name: str) -> list[dict]:
    return [json.loads(line) for line in (FIXTURES / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()]


def test_llm003_fixtures_have_expected_sizes_languages_and_gold_provenance() -> None:
    expected_sizes = {"planner": 30, "analyst": 18, "graph": 48}
    for role, expected_size in expected_sizes.items():
        cases = load(role)
        assert len(cases) == expected_size
        assert len({case["case_id"] for case in cases}) == expected_size
        assert {case["language"] for case in cases} == {"en", "ru", "mixed"}
        assert all(case.get("provenance") == "synthetic-CC0" for case in cases)


def test_graph_fixture_contains_positive_and_negative_gold_cases() -> None:
    cases = load("graph")
    positives = [case for case in cases if not case["negative"]]
    negatives = [case for case in cases if case["negative"]]
    assert len(positives) >= 24
    assert len(negatives) >= 20
    assert all(case["expected"] for case in positives)
    assert all(not case["expected"] for case in negatives)


def test_russian_fixture_text_is_valid_utf8_content() -> None:
    planner_ru = next(case for case in load("planner") if case["case_id"] == "PL-02")
    assert planner_ru["query"].startswith("\u0421\u043e\u0437\u0434\u0430\u0439")
