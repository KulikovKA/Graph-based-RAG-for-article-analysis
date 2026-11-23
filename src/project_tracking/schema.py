"""Проверка полей агрегированных событий перед передачей в tracking."""

from __future__ import annotations

import math
import re
from datetime import datetime

EXPERIMENTS = ("data_expansion", "retrieval_quality", "llm_as_judge")

_COMMON_PARAMS = {"git_commit", "config_hash", "corpus_hash", "graph_fingerprint", "schema_version"}
_PARAMS = {
    "data_expansion": _COMMON_PARAMS | {
        "dag_id", "run_id", "data_interval_start", "data_interval_end",
        "execution_timestamp", "source", "corpus_manifest_hash",
    },
    "retrieval_quality": _COMMON_PARAMS | {
        "retrieval_profile", "embedding_model", "embedding_revision", "entity_linking_config_hash",
        "bfs_depth", "bfs_limit", "reranker", "seed", "top_k", "split", "snapshot_hash",
    },
    "llm_as_judge": _COMMON_PARAMS | {
        "judge_model", "generator_model", "rubric_version", "prompt_version",
        "dataset_hash", "split", "snapshot_hash",
    },
}
_METRICS = {
    "data_expansion": {
        "pages", "revisions", "epo_ops_pages", "epo_ops_revisions", "openalex_pages",
        "openalex_revisions", "pipeline_seconds", "documents_found", "documents_new",
        "revisions_updated",
        "documents_skipped", "duplicates", "entities_added", "factual_relations_added",
        "semantic_relations_added", "concept_relations_added", "ingestion_seconds",
        "embedding_seconds", "neo4j_update_seconds", "qdrant_update_seconds",
        "stages_succeeded", "stages_failed", "retries", "resumes", "qa_gates_passed",
    },
    "retrieval_quality": {
        "factual_gold_doc_recall_at_k", "all_required_docs_at_k", "mrr", "ndcg",
        "evidence_coverage", "latency_p50_ms", "latency_p95_ms", "peak_rss_bytes",
        "questions_count", "input_tokens", "output_tokens", "groq_cost_usd",
        "estimated_groq_cost_usd", "completion_attempts", "usage_reported_attempts",
    },
    "llm_as_judge": {
        "questions_count", "groundedness", "factual_accuracy", "completeness",
        "citation_correctness", "hallucination_rate", "pairwise_preference",
        "inter_annotator_agreement", "judge_human_agreement", "input_tokens",
        "output_tokens", "cost_usd", "latency_ms",
    },
}
_COMMON_TAGS = {"unavailable_fields", "imported"}
_TAGS = {
    "data_expansion": _COMMON_TAGS | {
        "execution_timestamp", "stage", "qa_status", "ack_status", "error_code",
    },
    "retrieval_quality": _COMMON_TAGS | {
        "evaluation_source", "annotation_status", "measurement_scope",
    },
    "llm_as_judge": _COMMON_TAGS | {"evaluation_source", "annotation_status"},
}
_ENUMS = {
    "source": {"epo_ops", "openalex", "mixed"},
    "split": {"DEV", "HOLDOUT", "CALIBRATION", "SMOKE"},
    "measurement_scope": {"groq_smoke", "snapshot_replay"},
    "imported": {"true", "false"},
    "stage": {
        "complete", "failed", "skipped", "discovery", "ingest", "projection", "qa", "publish",
    },
    "error_code": {
        "none", "stale_interval", "offline_increment_failed", "invalid_interval",
        "invalid_limits", "invalid_page", "invalid_cursor", "invalid_revision",
        "unsupported_source", "dependency_unavailable", "dependency_failure", "missing_ack",
        "quality_failed", "page_limit", "invalid_scope", "source_unavailable",
        "invalid_document", "revision_changed", "source_limit", "invalid_progress",
        "interval_page_limit",
    },
    "qa_status": {"passed", "failed", "NOT_AVAILABLE"},
    "ack_status": {"passed", "failed", "NOT_AVAILABLE"},
    "evaluation_source": {"operational", "gold", "human", "judge", "fixture", "NOT_AVAILABLE"},
    "annotation_status": {"verified", "unverified", "none", "NOT_AVAILABLE"},
}
_TIMESTAMPS = {"data_interval_start", "data_interval_end", "execution_timestamp"}
_INTEGER_PARAMS = {"schema_version", "bfs_depth", "bfs_limit", "seed", "top_k"}
_FRACTIONS = {
    "factual_gold_doc_recall_at_k", "all_required_docs_at_k", "mrr", "ndcg",
    "evidence_coverage", "groundedness", "factual_accuracy", "completeness",
    "citation_correctness", "hallucination_rate", "pairwise_preference",
}
_AGREEMENTS = {"inter_annotator_agreement", "judge_human_agreement"}
_GOLD = {"factual_gold_doc_recall_at_k", "all_required_docs_at_k", "mrr", "ndcg"}
_JUDGE_QUALITY = {
    "groundedness", "factual_accuracy", "completeness", "citation_correctness",
    "hallucination_rate", "pairwise_preference", "inter_annotator_agreement",
    "judge_human_agreement",
}
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/+@-]{0,127}$")
_HASH = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")


def _check_param(key: str, value: object) -> None:
    if key in _INTEGER_PARAMS:
        if (
            type(value) is not int
            or value < 0
            or (key in {"schema_version", "top_k"} and value == 0)
        ):
            raise ValueError(f"invalid {key}")
        if key == "schema_version" and value != 1:
            raise ValueError("unsupported schema_version")
        return
    if not isinstance(value, str) or not value or len(value) > 128:
        raise ValueError(f"invalid {key}")
    if key in _ENUMS:
        if value not in _ENUMS[key]:
            raise ValueError(f"invalid {key}")
    elif key in _TIMESTAMPS:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise ValueError
        except ValueError:
            raise ValueError(f"invalid {key}") from None
    elif key == "git_commit":
        if not _COMMIT.fullmatch(value):
            raise ValueError(f"invalid {key}")
    elif key.endswith("_hash") or key == "graph_fingerprint":
        if not _HASH.fullmatch(value):
            raise ValueError(f"invalid {key}")
    elif not _IDENTIFIER.fullmatch(value) or "://" in value or "@" in value:
        raise ValueError(f"invalid {key}")


def missing_metrics(experiment: str, observed: dict[str, object]) -> list[str]:
    """Вернуть имена измерений схемы, для которых нет наблюдений."""
    return sorted(_METRICS[experiment] - observed.keys())


def validate(
    experiment: str,
    params: dict[str, object],
    metrics: dict[str, object],
    tags: dict[str, object],
) -> None:
    """Проверить агрегированные поля. Недоступные метрики не передаются как числа."""
    if experiment not in EXPERIMENTS:
        raise ValueError("unknown experiment")
    for values, allowed in ((params, _PARAMS[experiment]), (metrics, _METRICS[experiment]),
                            (tags, _TAGS[experiment])):
        if not isinstance(values, dict) or not all(isinstance(key, str) for key in values):
            raise ValueError("invalid fields")
        if values.keys() - allowed:
            raise ValueError("unknown fields")
    for key, value in params.items():
        _check_param(key, value)
    for key, value in metrics.items():
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError(f"invalid {key}")
        if not math.isfinite(value) or value < (-1 if key in _AGREEMENTS else 0):
            raise ValueError(f"invalid {key}")
        if key in _FRACTIONS | _AGREEMENTS and value > 1:
            raise ValueError(f"invalid {key}")
    for key, value in tags.items():
        if key == "unavailable_fields":
            if not isinstance(value, str) or not value:
                raise ValueError("invalid unavailable_fields")
            fields = value.split(",")
            if len(fields) != len(set(fields)) or any(
                field not in _METRICS[experiment] for field in fields
            ):
                raise ValueError("invalid unavailable_fields")
            if any(field in metrics for field in fields):
                raise ValueError("unavailable metric has a value")
        elif key in _TIMESTAMPS:
            _check_param(key, value)
        elif not isinstance(value, str) or value not in _ENUMS[key]:
            raise ValueError(f"invalid {key}")
    if experiment == "retrieval_quality" and metrics:
        required = {"git_commit", "config_hash", "snapshot_hash", "retrieval_profile", "split"}
        if not required <= params.keys() or tags.get("evaluation_source") in (
            None, "NOT_AVAILABLE",
        ):
            raise ValueError("retrieval metrics require provenance")
    if experiment == "retrieval_quality" and _GOLD.intersection(metrics):
        if tags.get("annotation_status") != "verified" or tags.get("evaluation_source") != "gold":
            raise ValueError("gold metrics require verified gold")
        if not {"git_commit", "config_hash", "corpus_hash", "split"} <= params.keys():
            raise ValueError("gold metrics require provenance")
    if experiment == "llm_as_judge" and _JUDGE_QUALITY.intersection(metrics):
        required = {
            "judge_model", "generator_model", "rubric_version", "prompt_version",
            "dataset_hash", "split",
        }
        if not required <= params.keys() or tags.get("evaluation_source") in (
            None, "NOT_AVAILABLE",
        ):
            raise ValueError("judge metrics require provenance")
