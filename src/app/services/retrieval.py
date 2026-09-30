"""Bounded multi-channel candidate retrieval over a pinned index generation."""

import asyncio
import base64
import math
import unicodedata
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Any, Protocol
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.contracts import ChannelCoverageV1, CoverageV1, SourceCoverageV1
from app.domain.evidence import (
    CandidateEvidence,
    RetrievalQuery,
    RetrievalResult,
    RetrievalSubquery,
    RetrievalUnavailable,
)
from app.domain.graph import GraphEdgeType
from app.domain.planner import IdeaV1
from app.integrations.neo4j import Neo4jGraph
from app.integrations.qdrant import QdrantIndex, VectorHit
from app.services.indexing import IndexingService
from app.storage.models import (
    DocumentRevision,
    EvidenceChunk,
    GraphFact,
    IndexGeneration,
    IndexMember,
    SourceDocument,
)

MAX_QUERY_CHARS = 2000
MAX_SUBQUERIES = 8
MAX_SUBQUERY_CHARS = 512
RRF_K = 60
PUBLIC_SOURCES = ("epo_ops", "openalex")


class LightRAGCandidateProvider(Protocol):
    """Optional context adapter; returned IDs are re-resolved in PostgreSQL."""

    async def query(self, query: str, *, generation_id: UUID) -> object: ...


class Embedder(Protocol):
    async def embed(
        self, *, model_id: str, request_id: str, texts: list[str]
    ) -> list[list[float]]: ...


@dataclass(frozen=True)
class RetrievalConfig:
    total_limit: int = 50
    per_channel_limit: int = 50
    graph_limit_per_feature: int = 50
    max_features: int = MAX_SUBQUERIES
    rrf_k: int = RRF_K

    def __post_init__(self) -> None:
        if not 1 <= self.total_limit <= 50:
            raise ValueError("total_limit must be between 1 and 50")
        if not 1 <= self.per_channel_limit <= 50:
            raise ValueError("per_channel_limit must be between 1 and 50")
        if not 1 <= self.graph_limit_per_feature <= 100:
            raise ValueError("graph_limit_per_feature must be between 1 and 100")
        if not 1 <= self.max_features <= 8 or self.rrf_k < 1:
            raise ValueError("invalid retrieval config")


@dataclass(frozen=True)
class _ChannelResult:
    candidates: tuple[CandidateEvidence, ...]


def _bounded(value: str, limit: int) -> str:
    compact = " ".join(value.split())
    return compact[:limit].rstrip()


def build_retrieval_query(
    original_query: str, idea: IdeaV1, *, max_features: int = MAX_SUBQUERIES
) -> RetrievalQuery:
    """Build deterministic feature searches and always retain the original query."""
    original = _bounded(original_query, MAX_QUERY_CHARS)
    if not original:
        raise ValueError("original query is required")
    if len(original_query) > MAX_QUERY_CHARS:
        raise ValueError("original query exceeds 2000 characters")
    if not 1 <= max_features <= MAX_SUBQUERIES:
        raise ValueError("max_features must be between 1 and 8")
    subqueries = [RetrievalSubquery(original, None)]
    seen = {original.casefold()}
    features = sorted(idea.features, key=lambda feature: (-feature.weight, str(feature.id)))
    feature_count = 0
    for feature in features:
        feature_text = feature.normalized_term or feature.text
        text = _bounded(
            f"{idea.domain} {feature_text} {' '.join(idea.technologies[:2])} "
            f"{' '.join(idea.constraints[:2])}",
            MAX_SUBQUERY_CHARS,
        )
        if not text or text.casefold() in seen:
            continue
        subqueries.append(RetrievalSubquery(text, feature.id))
        seen.add(text.casefold())
        feature_count += 1
        if feature_count >= max_features:
            break
    return RetrievalQuery(original_query, tuple(subqueries))


def _canonical_url(value: str) -> str:
    try:
        parts = urlsplit(value.strip())
    except ValueError:
        return value.strip()
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[CandidateEvidence]], *, limit: int, k: int = RRF_K
) -> tuple[CandidateEvidence, ...]:
    """Fuse ranked channel/query lists, dedupe canonical sources, and choose one chunk/doc."""
    scores: dict[str, float] = defaultdict(float)
    channels: dict[str, set[str]] = defaultdict(set)
    chunk_scores: dict[tuple[str, UUID], float] = defaultdict(float)
    representatives: dict[tuple[str, UUID], CandidateEvidence] = {}
    for ranked in ranked_lists:
        ordered = sorted(
            ranked,
            key=lambda item: (-item.score, item.source, item.external_id, str(item.chunk_id)),
        )
        seen_in_list: set[str] = set()
        for rank, item in enumerate(ordered, start=1):
            key = _canonical_url(item.canonical_url) or f"{item.source}:{item.external_id}"
            if key in seen_in_list:
                continue
            seen_in_list.add(key)
            contribution = 1.0 / (k + rank)
            scores[key] += contribution
            channels[key].update(item.channels)
            chunk_key = (key, item.chunk_id)
            chunk_scores[chunk_key] += contribution
            previous = representatives.get(chunk_key)
            if previous is None or (item.section, str(item.chunk_id)) < (
                previous.section, str(previous.chunk_id)
            ):
                representatives[chunk_key] = item
    selected: list[CandidateEvidence] = []
    for key, score in scores.items():
        chunk_key = min(
            (candidate_key for candidate_key in chunk_scores if candidate_key[0] == key),
            key=lambda candidate_key: (
                -chunk_scores[candidate_key],
                representatives[candidate_key].section,
                str(candidate_key[1]),
            ),
        )
        selected.append(
            replace(
                representatives[chunk_key],
                channels=tuple(sorted(channels[key])),
                score=score,
            )
        )
    selected.sort(
        key=lambda item: (
            -item.score,
            item.source,
            item.external_id,
            str(item.document_id),
        )
    )
    return tuple(selected[:limit])


class CandidateRetrievalService:
    """Parallel Qdrant, PostgreSQL metadata and domain graph retrieval."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        qdrant: QdrantIndex,
        embedder: Embedder,
        graph: Neo4jGraph,
        *,
        graph_namespace: str,
        graph_vocabulary_version: str,
        lightrag: LightRAGCandidateProvider | None = None,
        config: RetrievalConfig | None = None,
    ) -> None:
        if not graph_namespace or not graph_vocabulary_version:
            raise ValueError("graph namespace and vocabulary version are required")
        self.session_factory = session_factory
        self.qdrant = qdrant
        self.embedder = embedder
        self.graph = graph
        self.graph_namespace = graph_namespace
        self.graph_vocabulary_version = graph_vocabulary_version
        self.lightrag = lightrag
        self.config = config or RetrievalConfig()

    async def search(
        self,
        *,
        original_query: str,
        idea: IdeaV1,
        generation_id: UUID,
        request_id: str,
    ) -> RetrievalResult:
        query = build_retrieval_query(
            original_query, idea, max_features=self.config.max_features
        )
        with self.session_factory() as session:
            generation = session.get(IndexGeneration, generation_id)
            if generation is None:
                raise LookupError("index generation not found")
            qdrant_version = generation.config_versions_json.get("qdrant", {})
            if qdrant_version.get("projection_version") != self.qdrant.spec.projection_version:
                raise ValueError("embedding projection version mismatch")

        tasks: dict[str, Any] = {
            "qdrant": self._qdrant_candidates(query, generation_id, request_id),
            "metadata": asyncio.to_thread(self._metadata_candidates, query, generation_id),
            "domain_graph": self._graph_candidates(idea, generation_id),
        }
        lightrag_enabled = self.lightrag is not None and bool(
            getattr(self.lightrag, "enabled", True)
        )
        if lightrag_enabled:
            tasks["lightrag_context"] = self._lightrag_candidates(query, generation_id)
        names = list(tasks)
        outcomes = await asyncio.gather(*tasks.values(), return_exceptions=True)

        results: dict[str, _ChannelResult] = {}
        errors: dict[str, bool] = {}
        for name, outcome in zip(names, outcomes, strict=True):
            if isinstance(outcome, asyncio.CancelledError):
                raise outcome
            if isinstance(outcome, _ChannelResult):
                results[name] = outcome
            else:
                errors[name] = True

        required_success = any(name in results for name in ("qdrant", "metadata", "domain_graph"))
        if not required_success:
            raise RetrievalUnavailable("all required retrieval channels are unavailable")

        ranked_lists: list[Sequence[CandidateEvidence]] = []
        for result in results.values():
            if result.candidates:
                ranked_lists.append(result.candidates)
        candidates = reciprocal_rank_fusion(
            ranked_lists, limit=self.config.total_limit, k=self.config.rrf_k
        )
        channel_coverage = [
            ChannelCoverageV1(
                channel=name,
                status=(
                    "unavailable"
                    if name in errors
                    else "disabled"
                    if name == "lightrag_context" and not lightrag_enabled
                    else "ok"
                    if results[name].candidates
                    else "empty"
                ),
                reason_code="CHANNEL_UNAVAILABLE" if name in errors else None,
            )
            for name in ("qdrant", "metadata", "domain_graph", "lightrag_context")
            if name in results or name in errors or name == "lightrag_context"
        ]
        found_sources = {candidate.source for candidate in candidates}
        any_required_error = any(name in errors for name in ("qdrant", "metadata", "domain_graph"))
        sources = [
            SourceCoverageV1(
                source=source,
                status="ok" if source in found_sources else "empty",
                reason_code=None,
            )
            for source in ("epo_ops", "openalex")
        ]
        return RetrievalResult(
            generation_id=generation_id,
            query=query,
            candidates=candidates,
            coverage=CoverageV1(
                sources=sources,
                channels=channel_coverage,
                partial=any_required_error or "lightrag_context" in errors,
                historical=False,
            ),
        )

    async def _qdrant_candidates(
        self, query: RetrievalQuery, generation_id: UUID, request_id: str
    ) -> _ChannelResult:
        texts = [item.text for item in query.subqueries]
        vectors = await self.embedder.embed(
            model_id=self.qdrant.spec.model_id, request_id=f"{request_id}:embed", texts=texts
        )
        if len(vectors) != len(texts):
            raise ValueError("embedding count mismatch")

        async def search_one(index: int) -> list[VectorHit]:
            with self.session_factory() as session:
                return await IndexingService(session, self.qdrant, self.embedder).search(
                    vectors[index], generation_id=generation_id,
                    limit=self.config.per_channel_limit,
                )

        hit_lists = await asyncio.gather(*(search_one(index) for index in range(len(vectors))))
        all_hits: dict[UUID, VectorHit] = {}
        for hits in hit_lists:
            for hit in hits:
                old = all_hits.get(hit.chunk_id)
                if old is None or hit.score > old.score:
                    all_hits[hit.chunk_id] = hit
        return _ChannelResult(
            self._load_candidates(list(all_hits.values()), generation_id, "qdrant")
        )

    def _metadata_candidates(
        self, query: RetrievalQuery, generation_id: UUID
    ) -> _ChannelResult:
        with self.session_factory() as session:
            tsqueries = [func.plainto_tsquery("simple", item.text) for item in query.subqueries]
            document_text = func.to_tsvector(
                "simple", func.concat_ws(" ", SourceDocument.title, EvidenceChunk.text)
            )
            predicates = [document_text.op("@@")(tsquery) for tsquery in tsqueries]
            rank = func.greatest(
                *(func.ts_rank(document_text, tsquery) for tsquery in tsqueries)
            ).label("rank")
            rows = session.execute(
                select(EvidenceChunk, DocumentRevision, SourceDocument, rank)
                .join(DocumentRevision, DocumentRevision.id == EvidenceChunk.revision_id)
                .join(SourceDocument, SourceDocument.id == DocumentRevision.document_id)
                .join(
                    IndexMember,
                    (IndexMember.document_id == SourceDocument.id)
                    & (IndexMember.revision_id == DocumentRevision.id),
                )
                .where(IndexMember.generation_id == generation_id, or_(*predicates))
                .where(SourceDocument.source.in_(PUBLIC_SOURCES))
                .order_by(rank.desc(), SourceDocument.source, SourceDocument.external_id,
                          EvidenceChunk.id)
                .limit(self.config.per_channel_limit)
            ).all()
        candidates = tuple(
            self._candidate(chunk, revision, document, ("metadata",), float(score))
            for chunk, revision, document, score in rows
        )
        return _ChannelResult(candidates)

    async def _graph_candidates(
        self, idea: IdeaV1, generation_id: UUID
    ) -> _ChannelResult:
        features = sorted(idea.features, key=lambda feature: (-feature.weight, str(feature.id)))[
            : self.config.max_features
        ]
        feature_keys = {
            self._feature_key(feature.normalized_term or feature.text) for feature in features
        }
        if not feature_keys:
            return _ChannelResult(())
        records = await asyncio.gather(
            *(
                self.graph.one_hop(key, limit=self.config.graph_limit_per_feature)
                for key in sorted(feature_keys)
            )
        )
        fact_ids: set[UUID] = set()
        for group in records:
            for record in group:
                if record.edge_type != GraphEdgeType.DISCLOSES_FEATURE.value:
                    continue
                try:
                    fact_ids.add(UUID(str(record.properties.get("fact_id"))))
                except (ValueError, TypeError, AttributeError):
                    continue
        if not fact_ids:
            return _ChannelResult(())
        with self.session_factory() as session:
            rows = session.execute(
                select(GraphFact, EvidenceChunk, DocumentRevision, SourceDocument)
                .join(EvidenceChunk, EvidenceChunk.id == GraphFact.chunk_id)
                .join(DocumentRevision, DocumentRevision.id == GraphFact.revision_id)
                .join(SourceDocument, SourceDocument.id == DocumentRevision.document_id)
                .join(
                    IndexMember,
                    (IndexMember.document_id == SourceDocument.id)
                    & (IndexMember.revision_id == DocumentRevision.id),
                )
                .where(
                    GraphFact.id.in_(fact_ids),
                    GraphFact.edge_type == GraphEdgeType.DISCLOSES_FEATURE.value,
                    GraphFact.to_key.in_(feature_keys),
                    GraphFact.chunk_id.is_not(None),
                    GraphFact.confidence.is_not(None),
                    IndexMember.generation_id == generation_id,
                    SourceDocument.source.in_(PUBLIC_SOURCES),
                )
                .order_by(GraphFact.confidence.desc(), SourceDocument.source,
                          SourceDocument.external_id, EvidenceChunk.id)
                .limit(self.config.per_channel_limit)
            ).all()
        candidates = tuple(
            self._candidate(chunk, revision, document, ("domain_graph",), float(fact.confidence))
            for fact, chunk, revision, document in rows
            if fact.confidence is not None
            and fact.span_start is not None
            and fact.span_end is not None
            and 0 <= fact.span_start <= fact.span_end <= len(chunk.text)
            and chunk.text[fact.span_start : fact.span_end]
        )
        return _ChannelResult(candidates)

    async def _lightrag_candidates(
        self, query: RetrievalQuery, generation_id: UUID
    ) -> _ChannelResult:
        assert self.lightrag is not None
        # This protocol matches the optional context-only LightRAG adapter. Resolve returned
        # chunk IDs again against generation membership before accepting them.
        contexts = await asyncio.gather(
            *(
                self.lightrag.query(item.text, generation_id=generation_id)
                for item in query.subqueries
            )
        )
        chunk_ids: set[UUID] = set()
        successful = False
        for context in contexts:
            status = getattr(context, "status", "unavailable")
            if status in {"unavailable", "timeout"}:
                continue
            if status in {"success", "empty"}:
                successful = True
            for reference in getattr(context, "evidence", ()):
                chunk_id = getattr(reference, "chunk_id", None)
                if isinstance(chunk_id, UUID):
                    chunk_ids.add(chunk_id)
        if not successful:
            raise RuntimeError("LightRAG context unavailable")
        return _ChannelResult(
            self._load_candidates_by_chunk_ids(chunk_ids, generation_id, "lightrag_context")
        )

    def _load_candidates(
        self, hits: Sequence[VectorHit], generation_id: UUID, channel: str
    ) -> tuple[CandidateEvidence, ...]:
        return self._load_candidates_by_chunk_ids(
            {hit.chunk_id for hit in hits}, generation_id, channel,
            scores={hit.chunk_id: hit.score for hit in hits},
        )

    def _load_candidates_by_chunk_ids(
        self,
        chunk_ids: set[UUID],
        generation_id: UUID,
        channel: str,
        *,
        scores: dict[UUID, float] | None = None,
    ) -> tuple[CandidateEvidence, ...]:
        if not chunk_ids:
            return ()
        with self.session_factory() as session:
            rows = session.execute(
                select(EvidenceChunk, DocumentRevision, SourceDocument)
                .join(DocumentRevision, DocumentRevision.id == EvidenceChunk.revision_id)
                .join(SourceDocument, SourceDocument.id == DocumentRevision.document_id)
                .join(
                    IndexMember,
                    (IndexMember.document_id == SourceDocument.id)
                    & (IndexMember.revision_id == DocumentRevision.id),
                )
                .where(
                    EvidenceChunk.id.in_(chunk_ids),
                    IndexMember.generation_id == generation_id,
                    SourceDocument.source.in_(PUBLIC_SOURCES),
                )
            ).all()
        return tuple(
            self._candidate(
                chunk, revision, document, (channel,), (scores or {}).get(chunk.id, 1.0)
            )
            for chunk, revision, document in rows
        )

    @staticmethod
    def _candidate(
        chunk: EvidenceChunk,
        revision: DocumentRevision,
        document: SourceDocument,
        channels: tuple[str, ...],
        score: float,
    ) -> CandidateEvidence:
        return CandidateEvidence(
            document_id=document.id,
            revision_id=revision.id,
            chunk_id=chunk.id,
            source=document.source,
            external_id=document.external_id,
            canonical_url=document.canonical_url,
            title=document.title,
            kind=document.kind,
            publication_date=document.publication_date,
            section=chunk.section,
            language=chunk.language,
            text=chunk.text,
            channels=channels,
            score=score if math.isfinite(score) else 0.0,
        )

    def _feature_key(self, text: str) -> str:
        canonical = " ".join(unicodedata.normalize("NFKC", text).casefold().split())
        encoded = base64.urlsafe_b64encode(canonical.encode("utf-8")).decode("ascii").rstrip("=")
        return (
            f"{self.graph_namespace}:feature:{self.graph_vocabulary_version}:{encoded}"
        )
