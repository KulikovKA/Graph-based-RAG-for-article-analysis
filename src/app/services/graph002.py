"""Deterministic helpers for the isolated GRAPH-002 canonicalization experiment."""

from __future__ import annotations

import hashlib
import json
import re
import string
import unicodedata
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations
from typing import Any, Literal
from uuid import UUID, uuid5

GRAPH002_NAMESPACE = UUID("9bcefa39-c2dd-4f77-875b-d95ebfdc2ec2")
HYPHENS = "\u2010\u2011\u2012\u2013\u2014\u2015\u2212\ufe58\ufe63\uff0d"
HYPHEN_TRANSLATION = str.maketrans({char: "-" for char in HYPHENS})
_SPACE = re.compile(r"\s+")
_BETWEEN_WORDS_HYPHEN = re.compile(r"(?<=[\w])-(?=[\w])", re.UNICODE)
_DIGIT_DOT_DIGIT = re.compile(r"(?<=\d)\.(?=\d)")
_PUNCT_TRANSLATION = str.maketrans({char: " " for char in string.punctuation if char not in "+-"})


def normalize_feature_text(value: str) -> str:
    """Normalize presentation while retaining words, numbers, signs and qualifiers."""
    value = unicodedata.normalize("NFKC", value).casefold().strip()
    value = value.translate(HYPHEN_TRANSLATION)
    value = _BETWEEN_WORDS_HYPHEN.sub(" ", value)
    value = _DIGIT_DOT_DIGIT.sub("\ue000", value)
    value = value.translate(_PUNCT_TRANSLATION)
    value = value.replace("\ue000", ".")
    # Plus/minus remain tokens so polarity-bearing forms cannot vanish in cleanup.
    value = re.sub(r"(?<!\w)[+-]+(?!\w)", lambda match: f" {match.group(0)} ", value)
    return _SPACE.sub(" ", value).strip()


def deterministic_feature_id(run_id: UUID, canonical_key: str) -> UUID:
    return uuid5(GRAPH002_NAMESPACE, f"{run_id}:{canonical_key}")


def deterministic_resolution_id(run_id: UUID, graph_fact_id: UUID) -> UUID:
    return uuid5(GRAPH002_NAMESPACE, f"resolution:{run_id}:{graph_fact_id}")


def canonical_key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def pair_key(left: str, right: str) -> tuple[str, str]:
    if left == right:
        raise ValueError("feature pair must contain two different features")
    return (left, right) if left < right else (right, left)


def deduplicate_candidate_pairs(
    candidates: list[tuple[str, str, float]],
) -> dict[tuple[str, str], float]:
    """Collapse A-B/B-A candidate hits and keep the highest similarity."""
    result: dict[tuple[str, str], float] = {}
    for left, right, similarity in candidates:
        if left == right:
            continue
        key = pair_key(left, right)
        result[key] = max(result.get(key, -1.0), similarity)
    return result


def select_completed_active_records(
    records: Sequence[Any], *, vocabulary_version: str
) -> list[tuple[Any, Any, Any]]:
    """Pick the newest completed extraction for each document's active revision."""
    eligible = [
        (document, revision, state)
        for document, revision, state in records
        if document.active_revision_id == revision.id
        and state.revision_id == revision.id
        and state.vocabulary_version == vocabulary_version
        and isinstance(state.completed_at, datetime)
    ]
    eligible.sort(
        key=lambda row: (
            str(row[0].id),
            -row[2].completed_at.timestamp(),
            row[2].extractor_version,
        )
    )
    result = []
    seen: set[str] = set()
    for record in eligible:
        document_id = str(record[0].id)
        if document_id not in seen:
            result.append(record)
            seen.add(document_id)
    return result


def validate_checkpoint_compatibility(
    checkpoint: dict[str, Any], *, run_id: UUID, snapshot_hash: str, resolver_config: dict[str, Any]
) -> None:
    if checkpoint.get("schema_version") != 1:
        raise ValueError("checkpoint schema version is incompatible")
    if checkpoint.get("run_id") != str(run_id):
        raise ValueError("checkpoint run id mismatch")
    if checkpoint.get("snapshot_hash") != snapshot_hash:
        raise ValueError("checkpoint snapshot hash mismatch")
    if checkpoint.get("resolver_config") != resolver_config:
        raise ValueError("checkpoint resolver configuration mismatch")


def aggregate_shadow_edges(
    facts: list[dict[str, str]],
    *,
    fact_to_feature: dict[str, str],
    feature_to_canonical: dict[str, str],
) -> dict[tuple[str, str], int]:
    """Create one canonical edge per document/entity and count its supporting facts."""
    result: dict[tuple[str, str], int] = defaultdict(int)
    for fact in facts:
        fact_id = fact["graph_fact_id"]
        feature = fact_to_feature.get(fact_id)
        canonical = feature_to_canonical.get(feature) if feature is not None else None
        if canonical is not None:
            result[(fact["document_id"], canonical)] += 1
    return dict(result)


@dataclass(frozen=True)
class PairDecision:
    feature_a: str
    feature_b: str
    candidate_similarity: float
    decision: Literal["SAME", "DIFFERENT", "UNCERTAIN"]
    probabilities: dict[str, float]
    confidence: float

    @property
    def same_probability(self) -> float:
        return self.probabilities["SAME"]

    @property
    def cache_key(self) -> tuple[str, str]:
        return pair_key(self.feature_a, self.feature_b)


@dataclass(frozen=True)
class FeatureCluster:
    members: tuple[str, ...]
    canonical_text: str
    canonical_key: str
    document_count: int
    raw_aliases: tuple[str, ...]


@dataclass(frozen=True)
class ClusterConflict:
    candidate_pair: tuple[str, str]
    cannot_link_pair: tuple[str, str]


def constrained_clusters(
    features: set[str],
    decisions: list[PairDecision],
    *,
    threshold: float,
) -> tuple[list[tuple[str, ...]], list[ClusterConflict]]:
    """Greedily merge SAME pairs in stable confidence order, respecting cannot-links."""
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between zero and one")
    cannot_link = {decision.cache_key for decision in decisions if decision.decision == "DIFFERENT"}
    cannot_neighbors: dict[str, set[str]] = defaultdict(set)
    for left, right in cannot_link:
        cannot_neighbors[left].add(right)
        cannot_neighbors[right].add(left)
    accepted = [
        decision
        for decision in decisions
        if decision.decision == "SAME"
        and decision.same_probability >= threshold
        and decision.confidence >= threshold
    ]
    accepted.sort(
        key=lambda item: (
            -item.same_probability,
            -item.confidence,
            item.cache_key[0],
            item.cache_key[1],
        )
    )
    clusters: dict[str, set[str]] = {item: {item} for item in features}
    owner = {item: item for item in features}
    conflicts: list[ClusterConflict] = []
    for decision in accepted:
        left, right = decision.cache_key
        if left not in owner or right not in owner:
            continue
        left_root, right_root = owner[left], owner[right]
        if left_root == right_root:
            continue
        left_members, right_members = clusters[left_root], clusters[right_root]
        smaller, larger = sorted(
            (left_members, right_members), key=lambda members: (len(members), min(members))
        )
        blocked = None
        for member in sorted(smaller):
            conflicting = cannot_neighbors[member] & larger
            if conflicting:
                blocked = pair_key(member, min(conflicting))
                break
        if blocked is not None:
            conflicts.append(ClusterConflict((left, right), blocked))
            continue
        merged = left_members | right_members
        root = min(merged)
        clusters.pop(left_root)
        clusters.pop(right_root)
        clusters[root] = merged
        for member in merged:
            owner[member] = root
    result = [tuple(sorted(members)) for members in clusters.values()]
    result.sort(key=lambda members: members[0])
    return result, conflicts


def choose_canonical_label(
    members: tuple[str, ...],
    *,
    aliases: dict[str, set[str]],
    document_frequency: dict[str, int],
    vectors: dict[str, list[float]],
) -> tuple[str, tuple[str, ...]]:
    """Choose a deterministic existing alias, using an embedding medoid for clusters."""
    ordered_aliases = tuple(
        sorted({alias for member in members for alias in aliases.get(member, {member})})
    )
    if len(members) == 1:
        return members[0], ordered_aliases
    member_vectors = {member: vectors[member] for member in members if member in vectors}
    if len(member_vectors) != len(members):
        raise ValueError("medoid selection requires an embedding for every cluster member")

    def score(alias: str) -> tuple[float, int, int, str]:
        member = next(member for member in members if alias in aliases.get(member, {member}))
        vector = member_vectors[member]
        norm = sum(item * item for item in vector) ** 0.5
        similarities = []
        for other in member_vectors.values():
            other_norm = sum(item * item for item in other) ** 0.5
            if norm and other_norm:
                similarities.append(
                    sum(a * b for a, b in zip(vector, other, strict=False)) / (norm * other_norm)
                )
        medoid = sum(similarities) / len(similarities) if similarities else 0.0
        frequency = document_frequency.get(alias, 0)
        normalized = normalize_feature_text(alias)
        return (-medoid, -frequency, len(normalized), normalized + "\0" + alias)

    return min(ordered_aliases, key=score), ordered_aliases


def graph_metrics(
    documents: list[dict[str, str]],
    edges: list[tuple[str, str]],
    *,
    feature_metric_name: str,
    edge_count: int | None = None,
) -> dict[str, int | float]:
    """Compute document-feature connectivity using distinct document-feature edges."""
    doc_ids = [item["document_id"] for item in documents]
    all_docs = set(doc_ids)
    per_document: dict[str, set[str]] = {document_id: set() for document_id in doc_ids}
    feature_docs: dict[str, set[str]] = defaultdict(set)
    unique_edges = set(edges)
    for document_id, feature_id in unique_edges:
        if document_id not in all_docs:
            raise ValueError("graph edge references a document outside the snapshot")
        per_document[document_id].add(feature_id)
        feature_docs[feature_id].add(document_id)

    feature_count = len(feature_docs)
    shared_count = sum(
        len(documents_for_feature) > 1 for documents_for_feature in feature_docs.values()
    )
    singleton_count = feature_count - shared_count
    graph_documents = sum(bool(values) for values in per_document.values())
    zero_facts = len(all_docs) - graph_documents
    feature_counts = [len(values) for values in per_document.values()]
    edge_docs = {document_id for document_id, _ in unique_edges}
    pair_links: set[tuple[str, str]] = set()
    adjacency: dict[str, set[str]] = defaultdict(set)
    for document_id in all_docs:
        adjacency[f"d:{document_id}"]
    for feature_id, documents_for_feature in feature_docs.items():
        feature_node = f"f:{feature_id}"
        adjacency[feature_node]
        ordered_docs = sorted(documents_for_feature)
        pair_links.update(combinations(ordered_docs, 2))
        for document_id in ordered_docs:
            document_node = f"d:{document_id}"
            adjacency[document_node].add(feature_node)
            adjacency[feature_node].add(document_node)

    seen: set[str] = set()
    component_docs: list[int] = []
    component_nodes: list[int] = []
    for node in sorted(adjacency):
        if node in seen:
            continue
        stack = [node]
        seen.add(node)
        nodes = 0
        docs_in_component = 0
        while stack:
            current = stack.pop()
            nodes += 1
            docs_in_component += current.startswith("d:")
            for neighbor in adjacency[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        component_docs.append(docs_in_component)
        component_nodes.append(nodes)

    pct = shared_count * 100.0 / feature_count if feature_count else 0.0
    return {
        "processed_documents": len(all_docs),
        "graph_documents": graph_documents,
        feature_metric_name: feature_count,
        "raw_edges" if feature_metric_name == "raw_features" else "canonical_edges": (
            len(unique_edges) if edge_count is None else edge_count
        ),
        "documents_without_facts"
        if feature_metric_name == "raw_features"
        else "documents_without_canonical_facts": zero_facts,
        "zero_fact_percent": zero_facts * 100.0 / len(all_docs) if all_docs else 0.0,
        "shared_features"
        if feature_metric_name == "raw_features"
        else "shared_canonical_features": shared_count,
        "singleton_features"
        if feature_metric_name == "raw_features"
        else "singleton_canonical_features": singleton_count,
        "shared_feature_percent"
        if feature_metric_name == "raw_features"
        else "shared_canonical_feature_percent": pct,
        "features_per_document"
        if feature_metric_name == "raw_features"
        else "canonical_features_per_document": (
            sum(feature_counts) / len(all_docs) if all_docs else 0.0
        ),
        "edges_per_graph_document"
        if feature_metric_name == "raw_features"
        else "canonical_edges_per_document": (
            (len(unique_edges) if edge_count is None else edge_count) / len(edge_docs)
            if edge_docs
            else 0.0
        ),
        "connected_components": len(component_docs),
        "largest_component_documents": max(component_docs, default=0),
        "largest_component_nodes": max(component_nodes, default=0),
        "connected_document_pairs": len(pair_links),
    }


def stable_json_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
