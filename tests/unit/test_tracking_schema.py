import pytest

from project_tracking.schema import validate


def test_data_expansion_accepts_airflow_event() -> None:
    validate(
        "data_expansion",
        {
            "dag_id": "public_corpus_increment",
            "run_id": "scheduled__2026-11-23T00:00:00+00:00",
            "data_interval_start": "2026-11-22T00:00:00+00:00",
            "data_interval_end": "2026-11-23T00:00:00+00:00",
            "source": "openalex",
        },
        {"pages": 2, "revisions": 1, "epo_ops_pages": 1, "openalex_pages": 1,
         "pipeline_seconds": 2.3},
        {"stage": "complete", "error_code": "none", "unavailable_fields": "entities_added"},
    )


def test_gold_requires_verified_provenance() -> None:
    with pytest.raises(ValueError):
        validate("retrieval_quality", {}, {"mrr": 0.5}, {})
    validate(
        "retrieval_quality",
        {"git_commit": "a" * 40, "config_hash": "b" * 64, "corpus_hash": "c" * 64,
         "snapshot_hash": "d" * 64, "retrieval_profile": "baseline", "split": "DEV"},
        {"mrr": 0.5},
        {"evaluation_source": "gold", "annotation_status": "verified", "imported": "true"},
    )


def test_judge_fixture_and_missing_measurement() -> None:
    validate("llm_as_judge", {"judge_model": "fixture-v1", "generator_model": "fixture-v1",
                              "rubric_version": "v1", "prompt_version": "v1",
                              "dataset_hash": "a" * 64, "split": "DEV"}, {"groundedness": 0.9},
             {"evaluation_source": "fixture", "unavailable_fields": "cost_usd"})
    with pytest.raises(ValueError):
        validate("llm_as_judge", {}, {"cost_usd": 0}, {"unavailable_fields": "cost_usd"})


@pytest.mark.parametrize(
    ("params", "metrics", "tags"),
    [
        ({"prompt": "private"}, {}, {}),
        ({"judge_model": "private question"}, {}, {}),
        ({}, {"groundedness": float("nan")}, {}),
        ({}, {"groundedness": 1.1}, {}),
        ({}, {"input_tokens": True}, {}),
        ({}, {}, {"unavailable_fields": "private_prompt"}),
        ({}, {}, {"annotation_status": "arbitrary"}),
    ],
)
def test_rejects_unsafe_or_invalid_fields(params: dict, metrics: dict, tags: dict) -> None:
    with pytest.raises(ValueError):
        validate("llm_as_judge", params, metrics, tags)


def test_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError):
        validate("data_expansion", {"data_interval_start": "2026-01-01T00:00:00"}, {}, {})


def test_provenance_is_required_for_quality_metrics() -> None:
    with pytest.raises(ValueError):
        validate("retrieval_quality", {}, {"latency_p50_ms": 5}, {"evaluation_source": "fixture"})
    with pytest.raises(ValueError):
        validate("llm_as_judge", {}, {"groundedness": 0.7}, {"evaluation_source": "fixture"})
    with pytest.raises(ValueError):
        validate("data_expansion", {"schema_version": 2}, {}, {})
