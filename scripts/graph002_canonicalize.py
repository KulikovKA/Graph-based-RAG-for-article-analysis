"""Run resumable GRAPH-002 feature canonicalization against one active corpus snapshot."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import UUID, uuid4

import httpx
import yaml
from neo4j import AsyncGraphDatabase
from sqlalchemy import and_, delete, false, func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.inference import InferenceProvider
from app.integrations.inference_http import OllamaProvider
from app.integrations.neo4j import CanonicalNeo4jProjection
from app.integrations.qdrant import (
    FeatureEmbeddingIndex,
    FeatureEmbeddingSpec,
    FeatureVectorPoint,
)
from app.services.feature_equivalence import (
    FEATURE_EQUIVALENCE_CONTRACT,
    FeatureEquivalenceClassifier,
)
from app.services.graph002 import (
    PairDecision,
    aggregate_shadow_edges,
    canonical_key,
    choose_canonical_label,
    constrained_clusters,
    deduplicate_candidate_pairs,
    deterministic_feature_id,
    deterministic_resolution_id,
    graph_metrics,
    normalize_feature_text,
    pair_key,
    select_completed_active_records,
    stable_json_hash,
    validate_checkpoint_compatibility,
)
from app.services.graph_index import VOCABULARY_VERSION, decode_feature_key
from app.storage.models import (
    CanonicalFeature,
    CanonicalizationRun,
    DocumentRevision,
    EvidenceChunk,
    FeaturePairDecision,
    FeatureResolution,
    GraphExtractionState,
    GraphFact,
    SourceDocument,
)
from app.storage.repositories import make_engine, make_session_factory
from app.workers.inference import GenerationGate

RESOLVER_VERSION = "graph002-technical-feature-v1"
CHECKPOINT_SCHEMA_VERSION = 1
SAME_THRESHOLDS = (0.90, 0.95)
MANUAL_CASES = (
    ("transparency", "optical transparency"),
    ("room temperature", "room-temperature"),
    ("flexibility", "mechanical flexibility"),
    ("NO2 sensing", "gas sensing"),
    ("NO2 sensitivity", "NH3 sensitivity"),
    ("n-type", "p-type"),
    ("room-temperature operation", "room-temperature synthesis"),
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _load_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("model config is invalid")
    return config


def _config_identity(config: dict[str, Any], resolver_version: str) -> dict[str, Any]:
    embedding = config["embedding"]
    classifier = config["generation"]["relation_classifier"]
    if classifier.get("endpoint_type") != "systemone":
        raise ValueError("GRAPH-002 requires the configured SystemOne relation classifier")
    return {
        "resolver_version": resolver_version,
        "embedding_model_id": embedding["model_id"],
        "embedding_model_digest": embedding["digest"],
        "embedding_dimension": int(embedding["dimension"]),
        "classifier_model_id": classifier["model_id"],
        "classifier_model_digest": classifier["digest"],
        "classifier_contract": FEATURE_EQUIVALENCE_CONTRACT,
    }


def _capture_snapshot(
    sessions: sessionmaker[Session], *, graph_namespace: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with sessions() as session:
        active_document_count = int(
            session.scalar(
                select(func.count())
                .select_from(SourceDocument)
                .where(SourceDocument.active_revision_id.is_not(None))
            )
            or 0
        )
        rows = session.execute(
            select(SourceDocument, DocumentRevision, GraphExtractionState)
            .join(DocumentRevision, DocumentRevision.id == SourceDocument.active_revision_id)
            .join(GraphExtractionState, GraphExtractionState.revision_id == DocumentRevision.id)
            .where(
                SourceDocument.active_revision_id.is_not(None),
                GraphExtractionState.vocabulary_version == VOCABULARY_VERSION,
            )
            .order_by(
                SourceDocument.id,
                GraphExtractionState.completed_at.desc(),
                GraphExtractionState.extractor_version,
            )
        ).all()
        selected = select_completed_active_records(rows, vocabulary_version=VOCABULARY_VERSION)

        fact_predicates = [
            and_(
                GraphFact.revision_id == revision.id,
                GraphFact.extractor_version == state.extractor_version,
                GraphFact.vocabulary_version == state.vocabulary_version,
            )
            for _document, revision, state in selected
        ]
        facts = list(
            session.scalars(
                select(GraphFact)
                .where(or_(*fact_predicates) if fact_predicates else false())
                .order_by(GraphFact.revision_id, GraphFact.id)
            )
        )
        selected_states = {
            (revision.id, state.extractor_version, state.vocabulary_version): state
            for _document, revision, state in selected
        }
        counts: dict[tuple[UUID, str, str], int] = defaultdict(int)
        for fact in facts:
            counts[(fact.revision_id, fact.extractor_version, fact.vocabulary_version)] += 1
        for key, state in selected_states.items():
            if counts[key] != state.fact_count:
                raise RuntimeError(f"graph fact snapshot count mismatch for revision {key[0]}")

        feature_facts = [fact for fact in facts if fact.edge_type == "DISCLOSES_FEATURE"]
        chunk_ids = {fact.chunk_id for fact in feature_facts if fact.chunk_id is not None}
        chunks = (
            {
                chunk.id: chunk
                for chunk in session.scalars(
                    select(EvidenceChunk).where(EvidenceChunk.id.in_(chunk_ids))
                )
            }
            if chunk_ids
            else {}
        )
        document_by_revision: dict[UUID, SourceDocument] = {
            revision.id: document for document, revision, _state in selected
        }
        serialized_facts: list[dict[str, str]] = []
        runtime_facts: list[dict[str, Any]] = []
        for fact in feature_facts:
            document = document_by_revision.get(fact.revision_id)
            if document is None:
                continue
            raw_text = decode_feature_key(
                fact.to_key, namespace=graph_namespace, vocabulary_version=fact.vocabulary_version
            )
            serialized = {
                "graph_fact_id": str(fact.id),
                "document_id": str(document.id),
                "revision_id": str(fact.revision_id),
                "feature_key": fact.to_key,
                "raw_feature_text": raw_text,
            }
            serialized_facts.append(serialized)
            chunk = chunks.get(fact.chunk_id) if fact.chunk_id is not None else None
            quote = ""
            if (
                chunk is not None
                and fact.span_start is not None
                and fact.span_end is not None
                and 0 <= fact.span_start < fact.span_end <= len(chunk.text)
            ):
                quote = chunk.text[fact.span_start : fact.span_end]
            runtime_facts.append({**serialized, "context": quote})

        snapshot = {
            "created_at": _now(),
            "active_documents_total": active_document_count,
            "documents_excluded_missing_completed_graph_state": max(
                0, active_document_count - len(selected)
            ),
            "graph_namespace": graph_namespace,
            "vocabulary_version": VOCABULARY_VERSION,
            "documents": [
                {
                    "document_id": str(document.id),
                    "revision_id": str(revision.id),
                    "source": document.source,
                    "kind": document.kind,
                }
                for document, revision, _state in selected
            ],
            "extraction_states": [
                {
                    "revision_id": str(revision.id),
                    "extractor_version": state.extractor_version,
                    "vocabulary_version": state.vocabulary_version,
                    "fact_count": state.fact_count,
                    "completed_at": state.completed_at.isoformat(),
                }
                for _document, revision, state in selected
            ],
            "facts": serialized_facts,
        }
        snapshot["snapshot_hash"] = stable_json_hash(snapshot)
        return snapshot, runtime_facts


def _restore_snapshot_facts(
    sessions: sessionmaker[Session], snapshot: dict[str, Any], *, graph_namespace: str
) -> list[dict[str, Any]]:
    """Load only the frozen IDs in a snapshot, regardless of later corpus activation."""
    with sessions() as session:
        document_pairs = {
            (item["document_id"], item["revision_id"]) for item in snapshot["documents"]
        }
        document_ids = {UUID(document_id) for document_id, _revision_id in document_pairs}
        revisions = (
            {
                (str(revision.id), str(revision.document_id))
                for revision in session.scalars(
                    select(DocumentRevision).where(
                        DocumentRevision.id.in_(
                            [UUID(revision_id) for _, revision_id in document_pairs]
                        )
                    )
                )
            }
            if document_pairs
            else set()
        )
        if any(
            (revision_id, document_id) not in revisions
            for document_id, revision_id in document_pairs
        ):
            raise ValueError("snapshot contains a missing or mismatched document revision")
        if document_ids:
            existing_documents = set(
                session.scalars(
                    select(SourceDocument.id).where(SourceDocument.id.in_(document_ids))
                )
            )
            if existing_documents != document_ids:
                raise ValueError("snapshot contains a missing source document")

        for extraction in snapshot["extraction_states"]:
            state_key = (
                UUID(extraction["revision_id"]),
                extraction["extractor_version"],
                extraction["vocabulary_version"],
            )
            state = session.get(GraphExtractionState, state_key)
            if state is None or state.completed_at is None:
                raise ValueError("snapshot extraction state is no longer available or complete")
            if state.fact_count != extraction["fact_count"]:
                raise ValueError("snapshot extraction state count changed")

        expected_ids = {item["graph_fact_id"] for item in snapshot["facts"]}
        fact_rows = (
            list(
                session.scalars(
                    select(GraphFact).where(GraphFact.id.in_([UUID(item) for item in expected_ids]))
                )
            )
            if expected_ids
            else []
        )
        facts_by_id = {str(fact.id): fact for fact in fact_rows}
        if set(facts_by_id) != expected_ids:
            raise ValueError("one or more snapshot GraphFacts are no longer available")
        chunk_ids = {fact.chunk_id for fact in fact_rows if fact.chunk_id is not None}
        chunks = (
            {
                chunk.id: chunk
                for chunk in session.scalars(
                    select(EvidenceChunk).where(EvidenceChunk.id.in_(chunk_ids))
                )
            }
            if chunk_ids
            else {}
        )
        runtime_facts = []
        for item in snapshot["facts"]:
            fact = facts_by_id[item["graph_fact_id"]]
            if (
                str(fact.revision_id) != item["revision_id"]
                or fact.to_key != item["feature_key"]
                or fact.edge_type != "DISCLOSES_FEATURE"
            ):
                raise ValueError("snapshot GraphFact identity or feature key changed")
            raw_text = decode_feature_key(
                fact.to_key,
                namespace=graph_namespace,
                vocabulary_version=fact.vocabulary_version,
            )
            if raw_text != item["raw_feature_text"]:
                raise ValueError("snapshot raw feature text does not match its GraphFact key")
            chunk = chunks.get(fact.chunk_id) if fact.chunk_id is not None else None
            quote = ""
            if (
                chunk is not None
                and fact.span_start is not None
                and fact.span_end is not None
                and 0 <= fact.span_start < fact.span_end <= len(chunk.text)
            ):
                quote = chunk.text[fact.span_start : fact.span_end]
            runtime_facts.append({**item, "context": quote})
        return runtime_facts


def _snapshot_edges(snapshot: dict[str, Any]) -> tuple[list[dict[str, str]], list[tuple[str, str]]]:
    documents = [
        {"document_id": item["document_id"], "revision_id": item["revision_id"]}
        for item in snapshot["documents"]
    ]
    edges = [(item["document_id"], item["feature_key"]) for item in snapshot["facts"]]
    return documents, edges


def _before_metrics(snapshot: dict[str, Any]) -> dict[str, int | float]:
    documents, edges = _snapshot_edges(snapshot)
    return graph_metrics(
        documents,
        edges,
        feature_metric_name="raw_features",
        edge_count=len(snapshot["facts"]),
    )


def _checkpoint_save(path: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = _now()
    _write_json(path, state)


def _load_snapshot(path: Path) -> dict[str, Any]:
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("snapshot file is missing or invalid") from exc
    snapshot = body.get("snapshot") if isinstance(body, dict) else None
    if not isinstance(snapshot, dict):
        snapshot = body
    recorded_hash = snapshot.get("snapshot_hash")
    check_payload = {key: value for key, value in snapshot.items() if key != "snapshot_hash"}
    if not isinstance(recorded_hash, str) or stable_json_hash(check_payload) != recorded_hash:
        raise ValueError("snapshot hash validation failed")
    return cast(dict[str, Any], snapshot)


def _create_run(
    sessions: sessionmaker[Session],
    *,
    run_id: UUID,
    resolver_version: str,
    snapshot: dict[str, Any],
    config_identity: dict[str, Any],
    runtime_config: dict[str, Any],
) -> None:
    stored_config = {
        **config_identity,
        **runtime_config,
        "started_at": _now(),
    }
    with sessions() as session, session.begin():
        if session.get(CanonicalizationRun, run_id) is not None:
            raise ValueError("run id already exists; use --resume or --report-only")
        session.add(
            CanonicalizationRun(
                id=run_id,
                resolver_version=resolver_version,
                snapshot_hash=snapshot["snapshot_hash"],
                embedding_model_id=config_identity["embedding_model_id"],
                embedding_model_digest=config_identity["embedding_model_digest"],
                classifier_model_id=config_identity["classifier_model_id"],
                classifier_model_digest=config_identity["classifier_model_digest"],
                config_json=stored_config,
                snapshot_json=snapshot,
                status="running",
            )
        )


def _resume_run(
    sessions: sessionmaker[Session],
    *,
    run_id: UUID,
    snapshot: dict[str, Any],
    config_identity: dict[str, Any],
    runtime_config: dict[str, Any],
) -> CanonicalizationRun:
    with sessions() as session, session.begin():
        run = session.get(CanonicalizationRun, run_id)
        if run is None:
            raise ValueError("checkpoint run id is absent from PostgreSQL")
        if run.snapshot_hash != snapshot["snapshot_hash"] or run.snapshot_json != snapshot:
            raise ValueError("resume snapshot does not match the immutable PostgreSQL snapshot")
        expected = {**config_identity, **runtime_config}
        actual = {key: run.config_json.get(key) for key in expected}
        if actual != expected:
            raise ValueError("resume resolver/model configuration mismatch")
        if run.status == "completed":
            raise ValueError("run is already completed; use --report-only")
        run.status = "running"
        run.completed_at = None
        return run


def _load_decisions(
    sessions: sessionmaker[Session], run_id: UUID
) -> dict[tuple[str, str], PairDecision]:
    with sessions() as session:
        rows = session.scalars(
            select(FeaturePairDecision).where(FeaturePairDecision.run_id == run_id)
        )
        result = {}
        for row in rows:
            decision = PairDecision(
                feature_a=row.feature_a_key,
                feature_b=row.feature_b_key,
                candidate_similarity=float(row.candidate_similarity),
                decision=row.classifier_decision,  # type: ignore[arg-type]
                probabilities={key: float(value) for key, value in row.probabilities_json.items()},
                confidence=float(row.classifier_confidence),
            )
            result[decision.cache_key] = decision
        return result


def _save_decision(
    sessions: sessionmaker[Session], run_id: UUID, decision: PairDecision, latency_ms: float
) -> None:
    left, right = decision.cache_key
    with sessions() as session, session.begin():
        existing = session.scalar(
            select(FeaturePairDecision).where(
                FeaturePairDecision.run_id == run_id,
                FeaturePairDecision.feature_a_key == left,
                FeaturePairDecision.feature_b_key == right,
            )
        )
        if existing is None:
            session.add(
                FeaturePairDecision(
                    run_id=run_id,
                    feature_a_key=left,
                    feature_b_key=right,
                    candidate_similarity=decision.candidate_similarity,
                    classifier_decision=decision.decision,
                    probabilities_json=decision.probabilities,
                    classifier_confidence=decision.confidence,
                    latency_ms=latency_ms,
                )
            )


def _feature_groups(
    runtime_facts: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    groups: dict[str, dict[str, Any]] = {}
    fact_to_feature: dict[str, str] = {}
    for fact in runtime_facts:
        normalized = normalize_feature_text(fact["raw_feature_text"])
        if not normalized:
            continue
        group = groups.setdefault(
            normalized,
            {
                "aliases": set(),
                "documents": set(),
                "feature_keys": set(),
                "facts": [],
                "alias_documents": defaultdict(set),
                "contexts": [],
            },
        )
        group["aliases"].add(fact["raw_feature_text"])
        group["documents"].add(fact["document_id"])
        group["feature_keys"].add(fact["feature_key"])
        group["facts"].append(fact)
        group["alias_documents"][fact["raw_feature_text"]].add(fact["document_id"])
        context = fact.get("context", "")
        if context:
            group["contexts"].append((len(context), context, fact["graph_fact_id"]))
        fact_to_feature[fact["graph_fact_id"]] = normalized
    for group in groups.values():
        group["aliases"] = set(group["aliases"])
        group["documents"] = set(group["documents"])
        group["feature_keys"] = set(group["feature_keys"])
        group["representative_context"] = (
            min(group["contexts"])[1][:800] if group["contexts"] else ""
        )
        group["feature_key"] = min(group["feature_keys"])
        group["document_count"] = len(group["documents"])
    return groups, fact_to_feature


async def _preflight(
    *,
    inference_client: httpx.AsyncClient,
    qdrant_client: httpx.AsyncClient,
    driver: Any,
    config_identity: dict[str, Any],
) -> None:
    response = await inference_client.get("/api/tags", timeout=10)
    response.raise_for_status()
    models = response.json().get("models", [])
    installed = {item.get("name"): item.get("digest") for item in models}
    for name_key, digest_key in (
        ("embedding_model_id", "embedding_model_digest"),
        ("classifier_model_id", "classifier_model_digest"),
    ):
        model_id, expected_digest = config_identity[name_key], config_identity[digest_key]
        if installed.get(model_id) != expected_digest:
            raise RuntimeError(
                f"pinned model is not installed with its configured digest: {model_id}"
            )
    response = await qdrant_client.get("/collections", timeout=10)
    response.raise_for_status()
    await driver.verify_connectivity()


def _raw_alias_document_frequency(groups: dict[str, dict[str, Any]]) -> dict[str, int]:
    frequency: dict[str, set[str]] = defaultdict(set)
    for group in groups.values():
        for alias, documents in group["alias_documents"].items():
            frequency[alias].update(documents)
    return {alias: len(documents) for alias, documents in frequency.items()}


def _build_clusters(
    groups: dict[str, dict[str, Any]],
    decisions: list[PairDecision],
    vectors: dict[str, list[float]],
    *,
    threshold: float,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    membersets, conflicts = constrained_clusters(set(groups), decisions, threshold=threshold)
    alias_map = {key: value["aliases"] for key, value in groups.items()}
    alias_df = _raw_alias_document_frequency(groups)
    clusters: list[dict[str, Any]] = []
    feature_to_cluster: dict[str, str] = {}
    for members in membersets:
        label, aliases = choose_canonical_label(
            members,
            aliases=alias_map,
            document_frequency=alias_df,
            vectors=vectors,
        )
        docs = set().union(*(groups[member]["documents"] for member in members))
        key = canonical_key("\0".join(members))
        clusters.append(
            {
                "members": members,
                "canonical_text": label,
                "canonical_key": key,
                "document_count": len(docs),
                "raw_aliases": aliases,
                "raw_alias_count": len(
                    {alias for member in members for alias in groups[member]["aliases"]}
                ),
                "document_ids": docs,
            }
        )
        for member in members:
            feature_to_cluster[member] = key
    return clusters, [
        {
            "candidate_a": conflict.candidate_pair[0],
            "candidate_b": conflict.candidate_pair[1],
            "cannot_link_a": conflict.cannot_link_pair[0],
            "cannot_link_b": conflict.cannot_link_pair[1],
        }
        for conflict in conflicts
    ]


def _metrics_for_clusters(
    snapshot: dict[str, Any],
    runtime_facts: list[dict[str, Any]],
    clusters: list[dict[str, Any]],
    fact_to_feature: dict[str, str],
) -> dict[str, int | float]:
    feature_to_cluster = {
        member: cluster["canonical_key"] for cluster in clusters for member in cluster["members"]
    }
    semantic_edges = {
        (fact["document_id"], feature_to_cluster[fact_to_feature[fact["graph_fact_id"]]])
        for fact in runtime_facts
        if fact["graph_fact_id"] in fact_to_feature
    }
    documents = [
        {"document_id": item["document_id"], "revision_id": item["revision_id"]}
        for item in snapshot["documents"]
    ]
    return graph_metrics(
        documents,
        sorted(semantic_edges),
        feature_metric_name="canonical_features",
        edge_count=len(semantic_edges),
    )


def _decision_samples(
    decisions: list[PairDecision],
    clusters: list[dict[str, Any]],
    conflicts: list[dict[str, str]],
    groups: dict[str, dict[str, Any]],
    *,
    selected_threshold: float,
) -> dict[str, Any]:
    cluster_for = {
        member: cluster["canonical_key"] for cluster in clusters for member in cluster["members"]
    }
    same = [
        {
            "feature_a": item.feature_a,
            "feature_b": item.feature_b,
            "candidate_similarity": item.candidate_similarity,
            "same_probability": item.same_probability,
            "confidence": item.confidence,
            "merged_at_selected_threshold": (
                cluster_for.get(item.feature_a) == cluster_for.get(item.feature_b)
            ),
        }
        for item in decisions
        if item.decision == "SAME"
        and cluster_for.get(item.feature_a) == cluster_for.get(item.feature_b)
    ]
    different = [item for item in decisions if item.decision == "DIFFERENT"]
    uncertain = [item for item in decisions if item.decision == "UNCERTAIN"]

    def summarize(items: list[PairDecision], limit: int = 20) -> list[dict[str, Any]]:
        ordered = sorted(items, key=lambda item: item.cache_key)
        return [
            {
                "feature_a": item.feature_a,
                "feature_b": item.feature_b,
                "candidate_similarity": item.candidate_similarity,
                "probabilities": item.probabilities,
                "confidence": item.confidence,
            }
            for item in ordered[:limit]
        ]

    normalized_lookup = {normalize_feature_text(key): key for key in groups}
    pair_lookup = {item.cache_key: item for item in decisions}
    manual = []
    for phrase_a, phrase_b in MANUAL_CASES:
        key_a = normalized_lookup.get(normalize_feature_text(phrase_a))
        key_b = normalized_lookup.get(normalize_feature_text(phrase_b))
        decision = (
            pair_lookup.get(pair_key(key_a, key_b)) if key_a and key_b and key_a != key_b else None
        )
        manual.append(
            {
                "requested_pair": [phrase_a, phrase_b],
                "present_in_snapshot": bool(key_a and key_b),
                "normalized_features": [key_a, key_b],
                "candidate_decision": decision.decision
                if decision
                else ("normalized_exact" if key_a and key_a == key_b else None),
                "probabilities": decision.probabilities if decision else None,
                "merged_at_selected_threshold": (
                    cluster_for.get(key_a) == cluster_for.get(key_b) if key_a and key_b else False
                ),
            }
        )
    return {
        "successful_merge_samples": same[:20],
        "different_samples": summarize(different),
        "uncertain_samples": summarize(uncertain),
        "manual_cases": manual,
        "selected_threshold": selected_threshold,
        "conflicts_prevented": conflicts,
    }


def _persist_materialization(
    sessions: sessionmaker[Session],
    *,
    run_id: UUID,
    resolver_version: str,
    groups: dict[str, dict[str, Any]],
    clusters: list[dict[str, Any]],
    runtime_facts: list[dict[str, Any]],
    fact_to_feature: dict[str, str],
    decisions: list[PairDecision],
) -> tuple[list[dict[str, Any]], dict[str, UUID]]:
    feature_to_cluster = {
        member: cluster["canonical_key"] for cluster in clusters for member in cluster["members"]
    }
    cluster_by_key = {cluster["canonical_key"]: cluster for cluster in clusters}
    feature_ids = {key: deterministic_feature_id(run_id, key) for key in cluster_by_key}
    decisions_by_feature: dict[str, list[PairDecision]] = defaultdict(list)
    for decision in decisions:
        decisions_by_feature[decision.feature_a].append(decision)
        decisions_by_feature[decision.feature_b].append(decision)

    document_clusters = aggregate_shadow_edges(
        runtime_facts,
        fact_to_feature=fact_to_feature,
        feature_to_canonical=feature_to_cluster,
    )
    projection_rows: list[dict[str, Any]] = []

    with sessions() as session, session.begin():
        session.execute(delete(FeatureResolution).where(FeatureResolution.run_id == run_id))
        session.execute(delete(CanonicalFeature).where(CanonicalFeature.run_id == run_id))
        canonical_rows: dict[str, CanonicalFeature] = {}
        for key, cluster in cluster_by_key.items():
            row = CanonicalFeature(
                id=feature_ids[key],
                run_id=run_id,
                canonical_text=cluster["canonical_text"],
                canonical_key=key,
                member_count=cluster["raw_alias_count"],
                document_count=cluster["document_count"],
            )
            session.add(row)
            canonical_rows[key] = row

        for fact in runtime_facts:
            normalized = fact_to_feature.get(fact["graph_fact_id"])
            if normalized is None:
                continue
            cluster_key = feature_to_cluster[normalized]
            cluster = cluster_by_key[cluster_key]
            canonical_text = cluster["canonical_text"]
            raw = fact["raw_feature_text"]
            related = sorted(
                decisions_by_feature.get(normalized, []),
                key=lambda item: (
                    -item.candidate_similarity,
                    -item.confidence,
                    item.cache_key,
                ),
            )
            chosen = related[0] if related else None
            if raw == canonical_text:
                method = "exact"
            elif len(cluster["members"]) > 1:
                method = "tev1_same"
            elif normalize_feature_text(raw) == normalized:
                method = "normalized_exact"
            else:
                method = "new_singleton"
            session.add(
                FeatureResolution(
                    id=deterministic_resolution_id(run_id, UUID(fact["graph_fact_id"])),
                    run_id=run_id,
                    graph_fact_id=UUID(fact["graph_fact_id"]),
                    canonical_feature_id=feature_ids[cluster_key],
                    raw_feature_text=raw,
                    normalized_feature_text=normalized,
                    resolution_method=method,
                    candidate_similarity=chosen.candidate_similarity if chosen else None,
                    classifier_decision=chosen.decision if chosen else None,
                    probabilities_json=chosen.probabilities if chosen else None,
                    classifier_confidence=chosen.confidence if chosen else None,
                    resolver_version=resolver_version,
                )
            )
        session.flush()

    for (document_id, cluster_key), evidence_count in sorted(document_clusters.items()):
        cluster = cluster_by_key[cluster_key]
        projection_rows.append(
            {
                "document_id": document_id,
                "canonical_key": cluster_key,
                "canonical_feature_id": str(feature_ids[cluster_key]),
                "canonical_text": cluster["canonical_text"],
                "member_count": cluster["raw_alias_count"],
                "document_count": cluster["document_count"],
                "evidence_count": evidence_count,
            }
        )
    return projection_rows, feature_ids


def _projection_rows(
    rows: list[dict[str, Any]], snapshot: dict[str, Any], graph_namespace: str
) -> list[dict[str, Any]]:
    documents = {item["document_id"]: item for item in snapshot["documents"]}
    result = []
    for item in rows:
        document = documents[item["document_id"]]
        if document["source"] == "epo_ops":
            prefix, label = "patent", "Patent"
        elif document["source"] == "openalex":
            prefix, label = "work", "ScientificWork"
        else:
            raise ValueError("snapshot contains an unsupported document source")
        document_key = (
            f"{graph_namespace}:{prefix}:{document['document_id']}:rev:{document['revision_id']}"
        )
        result.append(
            {
                "document_label": label,
                "document_key": document_key,
                **{key: value for key, value in item.items() if key not in {"document_id", "fact"}},
            }
        )
    return result


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_reports(
    *,
    report_dir: Path,
    run_id: UUID,
    resolver_version: str,
    snapshot: dict[str, Any],
    before: dict[str, int | float],
    after: dict[str, int | float],
    sensitivities: dict[str, dict[str, int | float]],
    decisions: list[PairDecision],
    clusters: list[dict[str, Any]],
    conflicts: list[dict[str, str]],
    groups: dict[str, dict[str, Any]],
    counts: dict[str, Any],
    timings: dict[str, float],
    qdrant_collection: str,
    selected_threshold: float,
) -> dict[str, Any]:
    report_dir.mkdir(parents=True, exist_ok=True)
    before_payload = {
        "experiment": "GRAPH-002",
        "snapshot_hash": snapshot["snapshot_hash"],
        "snapshot_created_at": snapshot["created_at"],
        "snapshot_document_count": len(snapshot["documents"]),
        "snapshot_graph_fact_count": len(snapshot["facts"]),
        "active_documents_total": snapshot.get(
            "active_documents_total", len(snapshot["documents"])
        ),
        "documents_excluded_missing_completed_graph_state": snapshot.get(
            "documents_excluded_missing_completed_graph_state", 0
        ),
        "metrics": before,
    }
    _write_json(report_dir / "before.json", before_payload)
    samples = _decision_samples(
        decisions,
        clusters,
        conflicts,
        groups,
        selected_threshold=selected_threshold,
    )
    after_payload = {
        "experiment": "GRAPH-002",
        "run_id": str(run_id),
        "resolver_version": resolver_version,
        "same_threshold": selected_threshold,
        "snapshot_hash": snapshot["snapshot_hash"],
        "snapshot_document_count": len(snapshot["documents"]),
        "snapshot_graph_fact_count": len(snapshot["facts"]),
        "active_documents_total": snapshot.get(
            "active_documents_total", len(snapshot["documents"])
        ),
        "documents_excluded_missing_completed_graph_state": snapshot.get(
            "documents_excluded_missing_completed_graph_state", 0
        ),
        "metrics": after,
        "candidate_pairs": len(decisions),
        "same_count": sum(item.decision == "SAME" for item in decisions),
        "different_count": sum(item.decision == "DIFFERENT" for item in decisions),
        "uncertain_count": sum(item.decision == "UNCERTAIN" for item in decisions),
        "merged_raw_features": max(
            0, len({item["feature_key"] for item in snapshot["facts"]}) - len(clusters)
        ),
        "average_aliases_per_canonical_feature": (
            sum(item["raw_alias_count"] for item in clusters) / len(clusters) if clusters else 0.0
        ),
        "max_aliases_per_canonical_feature": max(
            (item["raw_alias_count"] for item in clusters), default=0
        ),
        "cannot_link_conflicts_prevented": len(conflicts),
        "latency_ms": timings,
        "qdrant_shadow_collection": qdrant_collection,
        "postgres_shadow_tables": [
            "canonicalization_runs",
            "canonical_features",
            "feature_pair_decisions",
            "feature_resolutions",
        ],
        "neo4j_shadow_label": "CanonicalTechnicalFeature",
        "neo4j_shadow_relationship": "DISCLOSES_CANONICAL_FEATURE",
        "neo4j_shadow_edges": counts.get("neo4j_shadow_edges", 0),
        "sensitivity": sensitivities,
        "quality_samples": samples,
        "errors": [],
    }
    _write_json(report_dir / "after.json", after_payload)
    comparison = {
        "snapshot_hash": snapshot["snapshot_hash"],
        "baseline": before,
        "canonical": after,
        "sensitivity": sensitivities,
    }
    _write_json(report_dir / "comparison.json", comparison)

    metrics_map = (
        ("documents", "processed_documents", "processed_documents"),
        ("feature nodes", "raw_features", "canonical_features"),
        ("edges", "raw_edges", "canonical_edges"),
        ("shared features", "shared_features", "shared_canonical_features"),
        ("shared feature %", "shared_feature_percent", "shared_canonical_feature_percent"),
        ("singleton %", "singleton_features", "singleton_canonical_features"),
        ("connected components", "connected_components", "connected_components"),
        ("largest component docs", "largest_component_documents", "largest_component_documents"),
        ("connected doc pairs", "connected_document_pairs", "connected_document_pairs"),
    )
    lines = [
        "# GRAPH-002 before/after comparison",
        "",
        f"Run: `{run_id}`  ",
        f"Resolver: `{resolver_version}`  ",
        f"Snapshot: `{snapshot['snapshot_hash']}` "
        f"({len(snapshot['documents'])} completed active revisions)",
        "",
        "All values below use the exact same immutable snapshot. Baseline tables, article chunks, "
        "TechnicalFeature nodes, and DISCLOSES_FEATURE relationships remain the production view.",
        "",
        f"| METRIC | BASELINE | CANONICAL ({selected_threshold:.2f}) | DELTA |",
        "|---|---:|---:|---:|",
    ]
    for title, base_key, canonical_metric in metrics_map:
        base_value = before.get(base_key, 0)
        canonical_value = after.get(canonical_metric, 0)
        if title == "singleton %":
            base_value = (
                100 * before.get("singleton_features", 0) / before.get("raw_features", 1)
                if before.get("raw_features", 0)
                else 0.0
            )
            canonical_value = (
                100
                * after.get("singleton_canonical_features", 0)
                / after.get("canonical_features", 1)
                if after.get("canonical_features", 0)
                else 0.0
            )
        delta = float(canonical_value) - float(base_value)
        lines.append(f"| {title} | {base_value:.2f} | {canonical_value:.2f} | {delta:+.2f} |")
    lines.extend(
        [
            "",
            "## Threshold sensitivity",
            "",
            (
                "| SAME probability and confidence threshold | Canonical features | "
                "Shared feature % | Components | Largest component documents | "
                "Connected document pairs |"
            ),
            "|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for threshold in SAME_THRESHOLDS:
        metrics = sensitivities[f"{threshold:.2f}"]
        lines.append(
            f"| {threshold:.2f} | {metrics['canonical_features']} | "
            f"{metrics['shared_canonical_feature_percent']:.2f} | "
            f"{metrics['connected_components']} | "
            f"{metrics['largest_component_documents']} | {metrics['connected_document_pairs']} |"
        )
    lines.extend(
        [
            "",
            f"Tev1 candidate pairs: {len(decisions)}; SAME: {after_payload['same_count']}; "
            f"DIFFERENT: {after_payload['different_count']}; "
            f"UNCERTAIN: {after_payload['uncertain_count']}; "
            f"cannot-link merges prevented: {len(conflicts)}.",
            "",
            "Quality examples and the requested manual cases are in `after.json`. The report keeps "
            "UNCERTAIN decisions and conflicts visible; it does not mark model-labeled merges as "
            "human-verified.",
        ]
    )
    (report_dir / "comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    same_rows = [
        {
            "feature_a": item.feature_a,
            "feature_b": item.feature_b,
            "candidate_similarity": item.candidate_similarity,
            "same_probability": item.same_probability,
            "confidence": item.confidence,
        }
        for item in decisions
        if item.decision == "SAME"
    ]
    uncertain_rows = [
        {
            "feature_a": item.feature_a,
            "feature_b": item.feature_b,
            "candidate_similarity": item.candidate_similarity,
            "uncertain_probability": item.probabilities["UNCERTAIN"],
            "confidence": item.confidence,
        }
        for item in decisions
        if item.decision == "UNCERTAIN"
    ]
    _write_csv(
        report_dir / "same_pairs.csv",
        same_rows,
        ["feature_a", "feature_b", "candidate_similarity", "same_probability", "confidence"],
    )
    _write_csv(
        report_dir / "uncertain_pairs.csv",
        uncertain_rows,
        [
            "feature_a",
            "feature_b",
            "candidate_similarity",
            "uncertain_probability",
            "confidence",
        ],
    )
    _write_csv(
        report_dir / "conflicts.csv",
        conflicts,
        ["candidate_a", "candidate_b", "cannot_link_a", "cannot_link_b"],
    )
    _write_csv(
        report_dir / "clusters.csv",
        [
            {
                "canonical_text": cluster["canonical_text"],
                "canonical_key": cluster["canonical_key"],
                "members": " | ".join(cluster["members"]),
                "raw_aliases": " | ".join(cluster["raw_aliases"]),
                "member_count": cluster["raw_alias_count"],
                "document_count": cluster["document_count"],
            }
            for cluster in clusters
        ],
        [
            "canonical_text",
            "canonical_key",
            "members",
            "raw_aliases",
            "member_count",
            "document_count",
        ],
    )
    readme = f"""# GRAPH-002 — TechnicalFeature Canonicalization

Run: `{run_id}`<br>
Resolver: `{resolver_version}`<br>
Snapshot: `{snapshot["snapshot_hash"]}`<br>
Documents: {len(snapshot["documents"])} active revisions with completed graph extraction<br>
GraphFacts: {len(snapshot["facts"])} `DISCLOSES_FEATURE` facts<br>
Qdrant shadow collection: `{qdrant_collection}`

The report compares the production baseline and canonical shadow graph on this exact snapshot.
The baseline `GraphFact`, `TechnicalFeature`, `DISCLOSES_FEATURE`, article-chunk collection,
extractor, and retrieval path were not changed. Canonicalization decisions and `GraphFact`
resolutions are in the four `canonicalization_runs`, `canonical_features`,
`feature_pair_decisions`, and `feature_resolutions` PostgreSQL tables.

Artifacts:

- `before.json` — baseline graph metrics
- `after.json` — {selected_threshold:.2f} materialization, decision counts,
  quality samples, and timing
- `comparison.json` / `comparison.md` — same-snapshot comparison and 0.90/0.95 sensitivity
- `same_pairs.csv`, `uncertain_pairs.csv`, `conflicts.csv`, `clusters.csv` — review data

If this run stopped before completion, resume it with:

```powershell
python scripts/graph002_canonicalize.py `
  --run-id {run_id} `
  --checkpoint data/checkpoints/graph002/{run_id}.json `
  --resume
```

For another run, apply the additive PostgreSQL migration first with `alembic upgrade head`.
The configured Qwen3 Embedding 0.6B and Tev1:4b digests are checked against the installed
inference runtime; the runner does not pull models.

## Neo4j queries for the morning review

Baseline graph:

```cypher
MATCH p=(d)-[:DISCLOSES_FEATURE]->(f:TechnicalFeature)
RETURN p
LIMIT 300;
```

Canonical shadow graph:

```cypher
MATCH p=(d)-[:DISCLOSES_CANONICAL_FEATURE]->(f:CanonicalTechnicalFeature)
RETURN p
LIMIT 300;
```

Only shared canonical features:

```cypher
MATCH (d)-[:DISCLOSES_CANONICAL_FEATURE]->(f:CanonicalTechnicalFeature)
WITH f, collect(DISTINCT d) AS docs
WHERE size(docs) > 1
UNWIND docs AS d
MATCH p=(d)-[:DISCLOSES_CANONICAL_FEATURE]->(f)
RETURN p
LIMIT 300;
```

Top shared canonical features:

```cypher
MATCH (d)-[:DISCLOSES_CANONICAL_FEATURE]->(f:CanonicalTechnicalFeature)
WITH f, count(DISTINCT d) AS documents
RETURN
  f.canonical_text AS feature,
  documents
ORDER BY documents DESC
LIMIT 50;
```
"""
    (report_dir / "README.md").write_text(readme, encoding="utf-8")
    return after_payload


def _report_only(sessions: sessionmaker[Session], run_id: UUID, report_dir: Path) -> int:
    with sessions() as session:
        run = session.get(CanonicalizationRun, run_id)
        if run is None:
            raise ValueError("canonicalization run not found")
        pairs = list(
            session.scalars(select(FeaturePairDecision).where(FeaturePairDecision.run_id == run_id))
        )
        resolutions = list(
            session.scalars(select(FeatureResolution).where(FeatureResolution.run_id == run_id))
        )
        features = list(
            session.scalars(select(CanonicalFeature).where(CanonicalFeature.run_id == run_id))
        )
    snapshot = run.snapshot_json
    config_json = run.config_json
    runtime_facts = [{**item, "context": ""} for item in snapshot["facts"]]
    groups, fact_to_feature = _feature_groups(runtime_facts)
    feature_by_id = {str(item.id): item for item in features}
    fact_to_canonical_key = {
        str(item.graph_fact_id): feature_by_id[str(item.canonical_feature_id)].canonical_key
        for item in resolutions
        if str(item.canonical_feature_id) in feature_by_id
    }
    feature_to_canonical_key: dict[str, str] = {}
    cluster_members: dict[str, set[str]] = defaultdict(set)
    for fact_id, normalized in fact_to_feature.items():
        canonical = fact_to_canonical_key.get(fact_id)
        if canonical:
            feature_to_canonical_key[normalized] = canonical
            cluster_members[canonical].add(normalized)
    clusters = []
    for key, members in sorted(cluster_members.items()):
        feature = next(item for item in features if item.canonical_key == key)
        aliases = tuple(
            sorted({alias for member in members for alias in groups[member]["aliases"]})
        )
        document_ids = set().union(*(groups[member]["documents"] for member in members))
        clusters.append(
            {
                "members": tuple(sorted(members)),
                "canonical_text": feature.canonical_text,
                "canonical_key": key,
                "document_count": feature.document_count,
                "raw_aliases": aliases,
                "raw_alias_count": len(aliases),
                "document_ids": document_ids,
            }
        )
    decisions = [
        PairDecision(
            feature_a=item.feature_a_key,
            feature_b=item.feature_b_key,
            candidate_similarity=float(item.candidate_similarity),
            decision=item.classifier_decision,  # type: ignore[arg-type]
            probabilities={key: float(value) for key, value in item.probabilities_json.items()},
            confidence=float(item.classifier_confidence),
        )
        for item in pairs
    ]
    selected_threshold = float(config_json.get("same_threshold", 0.95))
    conflicts_by_threshold: dict[float, list[dict[str, str]]] = {}
    sensitivities: dict[str, dict[str, int | float]] = {}
    for threshold in SAME_THRESHOLDS:
        memberships, blocked = constrained_clusters(set(groups), decisions, threshold=threshold)
        metric_clusters = [
            {
                "members": members,
                "canonical_key": canonical_key("\0".join(members)),
                "document_count": len(
                    set().union(*(groups[member]["documents"] for member in members))
                ),
            }
            for members in memberships
        ]
        sensitivities[f"{threshold:.2f}"] = _metrics_for_clusters(
            snapshot, runtime_facts, metric_clusters, fact_to_feature
        )
        conflicts_by_threshold[threshold] = [
            {
                "candidate_a": item.candidate_pair[0],
                "candidate_b": item.candidate_pair[1],
                "cannot_link_a": item.cannot_link_pair[0],
                "cannot_link_b": item.cannot_link_pair[1],
            }
            for item in blocked
        ]
    selected_metrics = _metrics_for_clusters(snapshot, runtime_facts, clusters, fact_to_feature)
    result_summary = config_json.get("result_summary", {})
    counts = result_summary.get("counts", {})
    timings = result_summary.get("timings_ms", {})
    after_payload = _write_reports(
        report_dir=report_dir,
        run_id=run_id,
        resolver_version=run.resolver_version,
        snapshot=snapshot,
        before=_before_metrics(snapshot),
        after=selected_metrics,
        sensitivities=sensitivities,
        decisions=decisions,
        clusters=clusters,
        conflicts=conflicts_by_threshold.get(selected_threshold, []),
        groups=groups,
        counts=counts,
        timings=timings,
        qdrant_collection=config_json.get("qdrant_shadow_collection", "unknown"),
        selected_threshold=selected_threshold,
    )
    report_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        report_dir / "run-summary.json",
        {
            "run_id": str(run_id),
            "resolver_version": run.resolver_version,
            "snapshot_hash": run.snapshot_hash,
            "status": run.status,
            "canonical_features": len(features),
            "graph_fact_resolutions": len(resolutions),
            "candidate_pairs": len(pairs),
            "report_after_summary": after_payload,
        },
    )
    return 0


async def _run(args: argparse.Namespace) -> int:
    if args.report_only:
        if not os.getenv("DATABASE_URL"):
            raise RuntimeError("missing environment settings: DATABASE_URL")
        if args.run_id is None:
            raise ValueError("--report-only requires --run-id")
        engine = make_engine(os.environ["DATABASE_URL"])
        try:
            return _report_only(make_session_factory(engine), args.run_id, Path(args.report_dir))
        finally:
            engine.dispose()
    required = ("DATABASE_URL", "QDRANT_URL", "NEO4J_PASSWORD", "INFERENCE_BASE_URL")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"missing environment settings: {', '.join(missing)}")
    config_path = Path(os.getenv("MODEL_CONFIG_PATH", "config/models.yaml"))
    config = _load_config(config_path)
    resolver_version = args.resolver_version
    config_identity = _config_identity(config, resolver_version)
    graph_namespace = os.getenv("GRAPH_NAMESPACE", "article-analysis-domain-v1")
    run_id = args.run_id
    checkpoint_path = Path(args.checkpoint) if args.checkpoint else None
    if args.resume:
        if checkpoint_path is None or not checkpoint_path.exists():
            raise ValueError("--resume requires an existing --checkpoint")
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        checkpoint_run_id = UUID(checkpoint["run_id"])
        if run_id is not None and run_id != checkpoint_run_id:
            raise ValueError("--run-id does not match the checkpoint")
        run_id = checkpoint_run_id
        snapshot = checkpoint["snapshot"]
        if checkpoint.get("snapshot_hash") != snapshot.get("snapshot_hash"):
            raise ValueError("checkpoint snapshot hash mismatch")
        if checkpoint.get("config_identity") != config_identity:
            raise ValueError("checkpoint model or resolver version mismatch")
    else:
        run_id = run_id or uuid4()
        snapshot = None
        if args.snapshot and Path(args.snapshot).exists():
            snapshot = _load_snapshot(Path(args.snapshot))

    engine = make_engine(os.environ["DATABASE_URL"])
    sessions = make_session_factory(engine)
    report_dir = Path(args.report_dir)
    if snapshot is None:
        snapshot, runtime_facts = _capture_snapshot(sessions, graph_namespace=graph_namespace)
    else:
        runtime_facts = _restore_snapshot_facts(sessions, snapshot, graph_namespace=graph_namespace)

    before = _before_metrics(snapshot)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "status": "dry_run",
                    "snapshot_hash": snapshot["snapshot_hash"],
                    "snapshot_document_count": len(snapshot["documents"]),
                    "snapshot_graph_fact_count": len(snapshot["facts"]),
                    "baseline_metrics": before,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        engine.dispose()
        return 0

    embedding = config["embedding"]
    classifier_config = config["generation"]["relation_classifier"]
    feature_spec = FeatureEmbeddingSpec.from_config(resolver_version, config_path)
    runtime_config = {
        "top_k": args.top_k,
        "candidate_min_similarity": args.candidate_min_similarity,
        "same_threshold": args.same_threshold,
        "feature_vocabulary_version": VOCABULARY_VERSION,
        "qdrant_shadow_collection": feature_spec.collection,
        "sensitivity_thresholds": list(SAME_THRESHOLDS),
    }
    if args.resume:
        validate_checkpoint_compatibility(
            checkpoint,
            run_id=run_id,
            snapshot_hash=snapshot["snapshot_hash"],
            resolver_config=runtime_config,
        )
    if not args.resume:
        if run_id is None:
            raise RuntimeError("run id was not assigned")
        checkpoint_path = checkpoint_path or Path("data/checkpoints/graph002") / f"{run_id}.json"
        if checkpoint_path.exists():
            raise ValueError(f"checkpoint already exists; use --resume: {checkpoint_path}")
        _create_run(
            sessions,
            run_id=run_id,
            resolver_version=resolver_version,
            snapshot=snapshot,
            config_identity=config_identity,
            runtime_config=runtime_config,
        )
        checkpoint = {
            "schema_version": CHECKPOINT_SCHEMA_VERSION,
            "run_id": str(run_id),
            "resolver_version": resolver_version,
            "snapshot_hash": snapshot["snapshot_hash"],
            "snapshot": snapshot,
            "config_identity": config_identity,
            "resolver_config": runtime_config,
            "processed_features": [],
            "processed_pairs": [],
            "resolved_graph_facts": [],
            "errors": [],
            "timings_ms": {
                "embedding": 0.0,
                "candidate_retrieval": 0.0,
                "classifier": 0.0,
                "total": 0.0,
            },
            "status": "running",
            "created_at": _now(),
        }
        _write_json(
            Path(args.snapshot) if args.snapshot else checkpoint_path.with_suffix(".snapshot.json"),
            {"snapshot": snapshot},
        )
    else:
        assert checkpoint_path is not None
        if checkpoint.get("resolver_config") != runtime_config:
            raise ValueError("checkpoint top-k, threshold, or candidate floor mismatch")
        _resume_run(
            sessions,
            run_id=run_id,
            snapshot=snapshot,
            config_identity=config_identity,
            runtime_config=runtime_config,
        )

    _write_json(
        report_dir / "before.json",
        {
            "experiment": "GRAPH-002",
            "snapshot_hash": snapshot["snapshot_hash"],
            "snapshot_created_at": snapshot["created_at"],
            "snapshot_document_count": len(snapshot["documents"]),
            "snapshot_graph_fact_count": len(snapshot["facts"]),
            "metrics": before,
        },
    )

    inference_client = httpx.AsyncClient(
        base_url=os.environ["INFERENCE_BASE_URL"], timeout=httpx.Timeout(300, connect=10)
    )
    qdrant_client = httpx.AsyncClient(
        base_url=os.environ["QDRANT_URL"], timeout=httpx.Timeout(60, connect=10)
    )
    driver = AsyncGraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]),
    )
    provider: InferenceProvider = OllamaProvider(
        inference_client,
        gate=GenerationGate(waiting_capacity=0),
        model_revisions={
            config_identity["embedding_model_id"]: config_identity["embedding_model_digest"],
            config_identity["classifier_model_id"]: config_identity["classifier_model_digest"],
        },
        supported_efforts={config_identity["classifier_model_id"]: set()},
        embedding_batch_size=int(embedding.get("batch_size", 16)),
    )
    feature_index = FeatureEmbeddingIndex(qdrant_client, feature_spec)
    classifier = FeatureEquivalenceClassifier(
        inference_client,
        model_id=config_identity["classifier_model_id"],
        digest=config_identity["classifier_model_digest"],
        max_state_bytes=int(classifier_config.get("max_state_bytes", 6000)),
    )
    started = time.perf_counter()
    timings = {
        "embedding": float(checkpoint.get("timings_ms", {}).get("embedding", 0.0)),
        "candidate_retrieval": float(
            checkpoint.get("timings_ms", {}).get("candidate_retrieval", 0.0)
        ),
        "classifier": float(checkpoint.get("timings_ms", {}).get("classifier", 0.0)),
        "total": float(checkpoint.get("timings_ms", {}).get("total", 0.0)),
    }
    try:
        await _preflight(
            inference_client=inference_client,
            qdrant_client=qdrant_client,
            driver=driver,
            config_identity=config_identity,
        )
        await feature_index.ensure_collection()
        groups, fact_to_feature = _feature_groups(runtime_facts)
        normalized_features = sorted(groups)

        vectors = await feature_index.vectors(run_id=run_id)
        missing = [item for item in normalized_features if item not in vectors]
        if missing:
            embedding_started = time.perf_counter()
            embedded = await provider.embed(
                model_id=config_identity["embedding_model_id"],
                request_id=f"graph002:{run_id}:embeddings",
                texts=missing,
                timeout=300,
            )
            if len(embedded) != len(missing):
                raise RuntimeError("embedding count does not match unique feature count")
            timings["embedding"] += (time.perf_counter() - embedding_started) * 1000
            new_points = []
            for normalized, vector in zip(missing, embedded, strict=True):
                group = groups[normalized]
                point = FeatureVectorPoint(
                    normalized_feature_text=normalized,
                    raw_feature_text=min(group["aliases"]),
                    feature_key=group["feature_key"],
                    run_id=run_id,
                    document_count=group["document_count"],
                    vector=vector,
                )
                new_points.append(point)
                vectors[normalized] = vector
            await feature_index.upsert(new_points)
        checkpoint["processed_features"] = normalized_features
        checkpoint["timings_ms"] = timings
        _checkpoint_save(checkpoint_path, checkpoint)
        print(
            json.dumps(
                {"stage": "feature_embeddings_ready", "features": len(normalized_features)},
                ensure_ascii=False,
            ),
            flush=True,
        )

        candidate_hits: list[tuple[str, str, float]] = []
        retrieval_started = time.perf_counter()
        for feature in normalized_features:
            hits = await feature_index.query(
                vectors[feature], run_id=run_id, limit=min(args.top_k + 1, 100)
            )
            for hit in hits:
                candidate = hit.normalized_feature_text
                if candidate == feature or candidate not in groups:
                    continue
                if hit.score < args.candidate_min_similarity:
                    continue
                candidate_hits.append((feature, candidate, min(1.0, max(-1.0, hit.score))))
        candidate_scores = deduplicate_candidate_pairs(candidate_hits)
        timings["candidate_retrieval"] += (time.perf_counter() - retrieval_started) * 1000
        sorted_pairs = sorted(candidate_scores.items())
        checkpoint["candidate_pairs"] = [list(key) for key, _score in sorted_pairs]
        checkpoint["timings_ms"] = timings
        _checkpoint_save(checkpoint_path, checkpoint)
        print(
            json.dumps(
                {"stage": "candidate_generation_complete", "pairs": len(sorted_pairs)},
                ensure_ascii=False,
            ),
            flush=True,
        )

        decisions_by_pair = _load_decisions(sessions, run_id)
        checkpoint["processed_pairs"] = [list(pair) for pair in sorted(decisions_by_pair)]
        checkpoint["processed_pair_count"] = len(decisions_by_pair)
        _checkpoint_save(checkpoint_path, checkpoint)
        for (left, right), similarity in sorted_pairs:
            if (left, right) in decisions_by_pair:
                continue
            a, b = groups[left], groups[right]
            decision = await classifier.classify(
                feature_a=left,
                feature_b=right,
                context_a=a["representative_context"],
                context_b=b["representative_context"],
                request_id=f"graph002:{run_id}:{stable_json_hash([left, right])[:16]}",
                timeout=120,
            )
            record = PairDecision(
                feature_a=left,
                feature_b=right,
                candidate_similarity=similarity,
                decision=decision.decision,
                probabilities=decision.probabilities,
                confidence=decision.confidence,
            )
            _save_decision(sessions, run_id, record, decision.latency_ms)
            decisions_by_pair[record.cache_key] = record
            checkpoint["processed_pair_count"] = len(decisions_by_pair)
            if len(decisions_by_pair) % 25 == 0:
                checkpoint["processed_pairs"] = [list(pair) for pair in sorted(decisions_by_pair)]
                _checkpoint_save(checkpoint_path, checkpoint)
                print(
                    json.dumps(
                        {
                            "stage": "classification_progress",
                            "processed_pairs": len(decisions_by_pair),
                            "candidate_pairs": len(sorted_pairs),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
        checkpoint["processed_pairs"] = [list(pair) for pair in sorted(decisions_by_pair)]
        checkpoint["processed_pair_count"] = len(decisions_by_pair)
        _checkpoint_save(checkpoint_path, checkpoint)
        with sessions() as session:
            timings["classifier"] = float(
                session.scalar(
                    select(func.coalesce(func.sum(FeaturePairDecision.latency_ms), 0.0)).where(
                        FeaturePairDecision.run_id == run_id
                    )
                )
                or 0.0
            )
        checkpoint["timings_ms"] = timings
        _checkpoint_save(checkpoint_path, checkpoint)
        decisions = [decisions_by_pair[key] for key in sorted(decisions_by_pair)]

        all_sensitivities: dict[str, dict[str, int | float]] = {}
        sensitivity_clusters: dict[float, list[dict[str, Any]]] = {}
        sensitivity_conflicts: dict[float, list[dict[str, str]]] = {}
        for threshold in SAME_THRESHOLDS:
            clusters_for_threshold, conflicts_for_threshold = _build_clusters(
                groups, decisions, vectors, threshold=threshold
            )
            sensitivity_clusters[threshold] = clusters_for_threshold
            sensitivity_conflicts[threshold] = conflicts_for_threshold
            all_sensitivities[f"{threshold:.2f}"] = _metrics_for_clusters(
                snapshot, runtime_facts, clusters_for_threshold, fact_to_feature
            )
        selected_clusters = sensitivity_clusters[args.same_threshold]
        selected_conflicts = sensitivity_conflicts[args.same_threshold]
        projection_rows, _feature_ids = _persist_materialization(
            sessions,
            run_id=run_id,
            resolver_version=resolver_version,
            groups=groups,
            clusters=selected_clusters,
            runtime_facts=runtime_facts,
            fact_to_feature=fact_to_feature,
            decisions=decisions,
        )
        checkpoint["resolved_graph_facts"] = [fact["graph_fact_id"] for fact in runtime_facts]
        checkpoint["cluster_state"] = {
            "threshold": args.same_threshold,
            "clusters": [list(item["members"]) for item in selected_clusters],
            "cannot_link_conflicts": selected_conflicts,
        }
        checkpoint["status"] = "materialized"
        _checkpoint_save(checkpoint_path, checkpoint)

        neo4j_projection = CanonicalNeo4jProjection(driver, namespace=graph_namespace)
        projected = await neo4j_projection.project(
            run_id=run_id,
            resolver_version=resolver_version,
            rows=_projection_rows(projection_rows, snapshot, graph_namespace),
        )
        after = all_sensitivities[f"{args.same_threshold:.2f}"]
        timings["total"] += (time.perf_counter() - started) * 1000
        counts = {
            "snapshot_documents": len(snapshot["documents"]),
            "snapshot_graph_facts": len(snapshot["facts"]),
            "unique_raw_feature_keys": len({item["feature_key"] for item in snapshot["facts"]}),
            "unique_normalized_features": len(groups),
            "candidate_pairs": len(candidate_scores),
            "classified_pairs": len(decisions),
            "canonical_features": len(selected_clusters),
            "neo4j_shadow_edges": projected,
            "errors": 0,
            "cannot_link_conflicts_prevented": len(selected_conflicts),
        }
        after_payload = _write_reports(
            report_dir=report_dir,
            run_id=run_id,
            resolver_version=resolver_version,
            snapshot=snapshot,
            before=before,
            after=after,
            sensitivities=all_sensitivities,
            decisions=decisions,
            clusters=selected_clusters,
            conflicts=selected_conflicts,
            groups=groups,
            counts=counts,
            timings=timings,
            qdrant_collection=feature_spec.collection,
            selected_threshold=args.same_threshold,
        )
        with sessions() as session, session.begin():
            run = session.get(CanonicalizationRun, run_id)
            if run is None:
                raise RuntimeError("canonicalization run disappeared")
            run.status = "completed"
            run.completed_at = datetime.now(UTC)
            run.config_json = {
                **run.config_json,
                "result_summary": {"counts": counts, "timings_ms": timings},
            }
        checkpoint.update(
            status="completed",
            completed_at=_now(),
            counts=counts,
            timings_ms=timings,
            report_after_summary=after_payload,
        )
        _checkpoint_save(checkpoint_path, checkpoint)
        print(
            json.dumps(
                {
                    "status": "completed",
                    "run_id": str(run_id),
                    **counts,
                    "timings_ms": timings,
                    "report_dir": str(report_dir),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    except KeyboardInterrupt:
        timings["total"] += (time.perf_counter() - started) * 1000
        checkpoint["timings_ms"] = timings
        checkpoint["status"] = "interrupted"
        _checkpoint_save(checkpoint_path, checkpoint)
        raise
    except Exception as exc:
        timings["total"] += (time.perf_counter() - started) * 1000
        checkpoint["timings_ms"] = timings
        checkpoint.setdefault("errors", []).append({"at": _now(), "type": type(exc).__name__})
        checkpoint["status"] = "failed"
        _checkpoint_save(checkpoint_path, checkpoint)
        with sessions() as session, session.begin():
            run = session.get(CanonicalizationRun, run_id)
            if run is not None:
                run.status = "failed"
        raise
    finally:
        await driver.close()
        await inference_client.aclose()
        await qdrant_client.aclose()
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=UUID)
    parser.add_argument("--resolver-version", default=RESOLVER_VERSION)
    parser.add_argument("--snapshot", help="read an immutable snapshot file or write one here")
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--candidate-min-similarity", type=float, default=0.60)
    parser.add_argument("--same-threshold", type=float, choices=SAME_THRESHOLDS, default=0.95)
    parser.add_argument("--checkpoint")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--report-dir", default="docs/validation/GRAPH-002")
    args = parser.parse_args()
    if not 1 <= args.top_k <= 64:
        parser.error("--top-k must be between 1 and 64")
    if not -1 <= args.candidate_min_similarity <= 1:
        parser.error("--candidate-min-similarity must be between -1 and 1")
    if args.resume and args.dry_run:
        parser.error("--resume and --dry-run cannot be combined")
    if args.report_only and (args.resume or args.dry_run):
        parser.error("--report-only cannot be combined with --resume or --dry-run")
    if args.resume and args.run_id is None and args.checkpoint is None:
        parser.error("--resume requires --checkpoint or --run-id")
    try:
        sys.exit(asyncio.run(_run(args)))
    except KeyboardInterrupt:
        run_id = args.run_id or "from-checkpoint"
        command = (
            "python scripts/graph002_canonicalize.py "
            f"--run-id {run_id} --checkpoint {args.checkpoint or '<checkpoint-path>'} --resume"
        )
        print(json.dumps({"status": "interrupted", "resume_command": command}), file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        safe_detail = str(exc) if isinstance(exc, ValueError | RuntimeError) else None
        print(
            json.dumps({"status": "failed", "error": type(exc).__name__, "detail": safe_detail}),
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
