"""Typed query and candidate records for generation-scoped retrieval."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.domain.contracts import CoverageV1


@dataclass(frozen=True)
class RetrievalSubquery:
    text: str
    feature_id: UUID | None


@dataclass(frozen=True)
class RetrievalQuery:
    original_query: str
    subqueries: tuple[RetrievalSubquery, ...]


@dataclass(frozen=True)
class CandidateEvidence:
    document_id: UUID
    revision_id: UUID
    chunk_id: UUID
    source: str
    external_id: str
    canonical_url: str
    title: str
    kind: str
    publication_date: date | None
    section: str
    language: str
    text: str
    channels: tuple[str, ...]
    score: float


@dataclass(frozen=True)
class RetrievalResult:
    generation_id: UUID
    query: RetrievalQuery
    candidates: tuple[CandidateEvidence, ...]
    coverage: CoverageV1

    @property
    def no_evidence(self) -> bool:
        return not self.candidates


class RetrievalUnavailable(RuntimeError):
    """Every configured retrieval channel failed for the pinned generation."""
