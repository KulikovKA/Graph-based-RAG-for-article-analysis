from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest

from app.domain.inference import InferenceProtocolError
from app.integrations.neo4j import CanonicalNeo4jProjection
from app.integrations.qdrant import (
    EmbeddingSpec,
    FeatureEmbeddingSpec,
    FeatureVectorPoint,
)
from app.services.feature_equivalence import (
    EQUIVALENCE_LABELS,
    FEATURE_EQUIVALENCE_CONTRACT,
    FeatureEquivalenceClassifier,
)
from app.services.graph002 import (
    PairDecision,
    aggregate_shadow_edges,
    choose_canonical_label,
    constrained_clusters,
    deduplicate_candidate_pairs,
    deterministic_feature_id,
    graph_metrics,
    normalize_feature_text,
    select_completed_active_records,
    validate_checkpoint_compatibility,
)
from app.services.graph_index import GraphIndexingService, decode_feature_key


def _decision(
    left: str,
    right: str,
    label: str,
    *,
    same: float = 1.0,
    confidence: float = 1.0,
    similarity: float = 0.9,
) -> PairDecision:
    probs = {name: 0.0 for name in EQUIVALENCE_LABELS}
    probs[label] = same if label == "SAME" else 0.99
    if label != "SAME":
        probs["SAME"] = 1.0 - probs[label]
    return PairDecision(left, right, similarity, label, probs, confidence)  # type: ignore[arg-type]


def test_feature_key_decode_is_exact_round_trip_and_rejects_other_namespace() -> None:
    service = object.__new__(GraphIndexingService)
    service.graph = cast(Any, SimpleNamespace(namespace="graph-unit-test"))
    service.vocabulary_version = "feature-test-v1"
    raw = "room-temperature / NO₂ sensing"
    key = service._feature_key(raw)
    assert (
        decode_feature_key(key, namespace="graph-unit-test", vocabulary_version="feature-test-v1")
        == raw
    )
    with pytest.raises(ValueError, match="namespace or vocabulary"):
        decode_feature_key(key, namespace="other", vocabulary_version="feature-test-v1")
    with pytest.raises(ValueError, match="payload"):
        decode_feature_key(
            "graph-unit-test:feature:feature-test-v1:%%%",
            namespace="graph-unit-test",
            vocabulary_version="feature-test-v1",
        )


@pytest.mark.parametrize(
    ("left", "right", "same"),
    [
        ("Room Temperature", "room-temperature", True),
        ("room   temperature", "room temperature", True),
        ("NO₂ sensitivity", "NO2 sensitivity", True),
        ("NO2 sensitivity", "NH3 sensitivity", False),
        ("n-type", "p-type", False),
        ("gas sensing", "NO2 sensing", False),
        ("room-temperature operation", "room-temperature synthesis", False),
        ("high temperature", "low temperature", False),
        ("with heating", "without heating", False),
        ("0.5 volt", "05 volt", False),
    ],
)
def test_normalization_is_deterministic_and_preserves_technical_tokens(
    left: str, right: str, same: bool
) -> None:
    assert (normalize_feature_text(left) == normalize_feature_text(right)) is same


def test_candidate_pair_deduplication_is_undirected_and_keeps_best_similarity() -> None:
    assert deduplicate_candidate_pairs([("A", "B", 0.7), ("B", "A", 0.9), ("A", "A", 1.0)]) == {
        ("A", "B"): 0.9
    }


def test_merge_requires_probability_and_confidence_threshold() -> None:
    low_probability = _decision("a", "b", "SAME", same=0.94, confidence=0.99)
    low_confidence = _decision("b", "c", "SAME", same=0.99, confidence=0.94)
    clusters, conflicts = constrained_clusters(
        {"a", "b", "c"}, [low_probability, low_confidence], threshold=0.95
    )
    assert clusters == [("a",), ("b",), ("c",)]
    assert conflicts == []


def test_cannot_link_prevents_bad_transitive_cluster_merge() -> None:
    decisions = [
        _decision("a", "b", "SAME", same=0.99, confidence=0.99),
        _decision("b", "c", "SAME", same=0.98, confidence=0.98),
        _decision("a", "c", "DIFFERENT"),
    ]
    clusters, conflicts = constrained_clusters({"a", "b", "c"}, decisions, threshold=0.95)
    assert clusters == [("a", "b"), ("c",)]
    assert conflicts[0].candidate_pair == ("b", "c")
    assert conflicts[0].cannot_link_pair == ("a", "c")


def test_canonical_label_tie_break_and_feature_id_are_reproducible() -> None:
    aliases = {"a": {"optical transparency"}, "b": {"transparency"}}
    docs = {"optical transparency": 4, "transparency": 4}
    vectors = {"a": [1.0, 0.0], "b": [1.0, 0.0]}
    first = choose_canonical_label(
        ("a", "b"), aliases=aliases, document_frequency=docs, vectors=vectors
    )
    assert first[0] == "transparency"
    assert first == choose_canonical_label(
        ("a", "b"), aliases=aliases, document_frequency=docs, vectors=vectors
    )
    run_id = uuid4()
    assert deterministic_feature_id(run_id, "cluster-key") == deterministic_feature_id(
        run_id, "cluster-key"
    )
    assert deterministic_feature_id(run_id, "cluster-key") != deterministic_feature_id(
        uuid4(), "cluster-key"
    )


def test_qdrant_shadow_collection_is_separate_and_feature_point_id_is_stable() -> None:
    model_id = "qwen3-embedding:0.6b"
    digest = "abc123"
    chunks = EmbeddingSpec("article-analysis-v1", model_id, digest, 1024)
    features = FeatureEmbeddingSpec(model_id, digest, 1024, "graph002-v1")
    assert features.collection != chunks.collection
    assert features.collection.startswith("graph_feature_mentions_")
    point = FeatureVectorPoint(
        "room temperature", "room-temperature", "key", uuid4(), 2, [0.1] * 1024
    )
    clone = FeatureVectorPoint(
        "room temperature", "room-temperature", "key", point.run_id, 2, [0.2] * 1024
    )
    assert point.point_id == clone.point_id


@pytest.mark.parametrize("label", EQUIVALENCE_LABELS)
def test_feature_equivalence_response_validation(label: str) -> None:
    probabilities = {name: float(name == label) for name in EQUIVALENCE_LABELS}
    body = {
        "model": "tev1:4b",
        "answers": {
            "equivalence": {
                "type": "choice",
                "choice": label,
                "probabilities": probabilities,
                "confidence": 0.98,
            }
        },
    }
    classifier = FeatureEquivalenceClassifier(None, model_id="tev1:4b", digest="digest")  # type: ignore[arg-type]
    validated = classifier._validate(body)
    assert validated[0] == label
    assert FEATURE_EQUIVALENCE_CONTRACT == "feature-equivalence-v1"


def test_feature_equivalence_rejects_inconsistent_response() -> None:
    body = {
        "model": "tev1:4b",
        "answers": {
            "equivalence": {
                "type": "choice",
                "choice": "SAME",
                "probabilities": {"SAME": 0.1, "DIFFERENT": 0.8, "UNCERTAIN": 0.1},
                "confidence": 0.9,
            }
        },
    }
    classifier = FeatureEquivalenceClassifier(None, model_id="tev1:4b", digest="digest")  # type: ignore[arg-type]
    with pytest.raises(InferenceProtocolError, match="contradicts probabilities"):
        classifier._validate(body)


def test_snapshot_selection_excludes_non_active_and_unfinished_revisions() -> None:
    document_id, active_revision, inactive_revision = uuid4(), uuid4(), uuid4()
    now = datetime.now(UTC)
    document = SimpleNamespace(id=document_id, active_revision_id=active_revision)
    active = SimpleNamespace(id=active_revision)
    inactive = SimpleNamespace(id=inactive_revision)
    complete = SimpleNamespace(
        revision_id=active_revision,
        vocabulary_version="v1",
        extractor_version="current",
        completed_at=now,
    )
    unfinished = SimpleNamespace(
        revision_id=active_revision,
        vocabulary_version="v1",
        extractor_version="unfinished",
        completed_at=None,
    )
    stale = SimpleNamespace(
        revision_id=inactive_revision,
        vocabulary_version="v1",
        extractor_version="stale",
        completed_at=now - timedelta(days=1),
    )
    selected = select_completed_active_records(
        [(document, active, unfinished), (document, inactive, stale), (document, active, complete)],
        vocabulary_version="v1",
    )
    assert len(selected) == 1
    assert selected[0][2] is complete


def test_duplicate_graph_facts_become_one_shadow_edge_with_evidence_count() -> None:
    doc_id = str(uuid4())
    facts = [{"graph_fact_id": f"fact-{index}", "document_id": doc_id} for index in range(3)]
    edges = aggregate_shadow_edges(
        facts,
        fact_to_feature={f"fact-{index}": "room temperature" for index in range(3)},
        feature_to_canonical={"room temperature": "canonical-key"},
    )
    assert edges == {(doc_id, "canonical-key"): 3}


def test_graph_metrics_preserve_evidence_count_and_bipartite_connectivity() -> None:
    doc_a, doc_b, doc_empty = str(uuid4()), str(uuid4()), str(uuid4())
    metrics = graph_metrics(
        [
            {"document_id": doc_a, "revision_id": str(uuid4())},
            {"document_id": doc_b, "revision_id": str(uuid4())},
            {"document_id": doc_empty, "revision_id": str(uuid4())},
        ],
        [(doc_a, "feature-a"), (doc_a, "feature-b"), (doc_b, "feature-a")],
        feature_metric_name="raw_features",
        edge_count=4,
    )
    assert metrics["processed_documents"] == 3
    assert metrics["graph_documents"] == 2
    assert metrics["raw_features"] == 2
    assert metrics["raw_edges"] == 4
    assert metrics["shared_features"] == 1
    assert metrics["singleton_features"] == 1
    assert metrics["shared_feature_percent"] == 50
    assert metrics["documents_without_facts"] == 1
    assert metrics["connected_components"] == 2
    assert metrics["largest_component_documents"] == 2
    assert metrics["largest_component_nodes"] == 4
    assert metrics["connected_document_pairs"] == 1
    assert metrics["edges_per_graph_document"] == 2


def test_shadow_projection_only_writes_canonical_relationship_and_evidence_count() -> None:
    statements: list[tuple[str, dict[str, object]]] = []

    class Result:
        def __init__(self, projected: int = 0) -> None:
            self.projected = projected

        async def single(self):  # type: ignore[no-untyped-def]
            return {"projected": self.projected}

        async def consume(self) -> None:
            return None

    class Session:
        async def __aenter__(self):  # type: ignore[no-untyped-def]
            return self

        async def __aexit__(self, *args):  # type: ignore[no-untyped-def]
            return None

        async def run(self, query: str, **kwargs):  # type: ignore[no-untyped-def]
            statements.append((query, kwargs))
            return Result()

        async def execute_write(self, callback):  # type: ignore[no-untyped-def]
            return await callback(Transaction())

    class Transaction:
        async def run(self, query: str, **kwargs):  # type: ignore[no-untyped-def]
            statements.append((query, kwargs))
            return Result(len(kwargs["rows"]))

    class Driver:
        def session(self, **kwargs):  # type: ignore[no-untyped-def]
            return Session()

    async def run_projection() -> int:
        projection = CanonicalNeo4jProjection(Driver(), namespace="graph-unit-test")  # type: ignore[arg-type]
        return await projection.project(
            run_id=uuid4(),
            resolver_version="graph002-v1",
            rows=[
                {
                    "document_label": "ScientificWork",
                    "document_key": "graph-unit-test:work:doc:rev:rev",
                    "canonical_feature_id": str(uuid4()),
                    "canonical_text": "room temperature",
                    "member_count": 2,
                    "document_count": 1,
                    "evidence_count": 3,
                }
            ],
        )

    import asyncio

    assert asyncio.run(run_projection()) == 1
    cypher = "\n".join(statement for statement, _kwargs in statements)
    assert "DISCLOSES_CANONICAL_FEATURE" in cypher
    assert "CanonicalTechnicalFeature" in cypher
    assert "DISCLOSES_FEATURE" not in cypher
    assert "SET source" not in cypher
    write_rows = next(kwargs["rows"] for query, kwargs in statements if "UNWIND $rows" in query)
    assert write_rows[0]["evidence_count"] == 3  # type: ignore[index]


def test_resume_checkpoint_rejects_snapshot_or_configuration_drift() -> None:
    run_id = uuid4()
    checkpoint = {
        "schema_version": 1,
        "run_id": str(run_id),
        "snapshot_hash": "same-snapshot",
        "resolver_config": {"top_k": 8},
    }
    validate_checkpoint_compatibility(
        checkpoint, run_id=run_id, snapshot_hash="same-snapshot", resolver_config={"top_k": 8}
    )
    with pytest.raises(ValueError, match="snapshot hash"):
        validate_checkpoint_compatibility(
            checkpoint, run_id=run_id, snapshot_hash="different", resolver_config={"top_k": 8}
        )
    with pytest.raises(ValueError, match="configuration"):
        validate_checkpoint_compatibility(
            checkpoint, run_id=run_id, snapshot_hash="same-snapshot", resolver_config={"top_k": 4}
        )
