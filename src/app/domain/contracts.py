"""Shared v1 DTOs. Business rules and persistence are intentionally out of scope here."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QuoteV1(StrictModel):
    evidence_id: UUID
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    text: str


class ClaimV1(StrictModel):
    text: str
    evidence_ids: list[UUID]
    quotes: list[QuoteV1]


class MatchV1(StrictModel):
    feature_id: UUID
    document_id: UUID
    claims: list[ClaimV1]


class DifferenceV1(StrictModel):
    feature_id: UUID
    claims: list[ClaimV1]


class LimitationV1(StrictModel):
    code: str
    message: str


class AnswerV1(StrictModel):
    schema_version: Literal[1] = 1
    summary: list[ClaimV1]
    matches: list[MatchV1]
    differences: list[DifferenceV1]
    limitations: list[LimitationV1]
    followup_suggestions: list[str]


class SourceCoverageV1(StrictModel):
    source: str
    status: Literal["ok", "empty", "unavailable", "not_configured", "not_requested"]
    reason_code: str | None = None


class ChannelCoverageV1(StrictModel):
    channel: str
    status: Literal["ok", "empty", "unavailable", "disabled"]
    reason_code: str | None = None


class CoverageV1(StrictModel):
    sources: list[SourceCoverageV1]
    channels: list[ChannelCoverageV1]
    partial: bool
    historical: bool


class SourceV1(StrictModel):
    document_id: UUID
    revision_id: UUID
    title: str
    kind: str
    publication_date: datetime | None = None
    url: str
    evidence_ids: list[UUID]


class RunV1(StrictModel):
    id: UUID
    status: Literal["pending", "running", "completed", "failed", "cancelled"]
    stage: str
    idea_version_id: UUID | None = None
    source_run_id: UUID | None = None
    outcome: Literal["analysis", "safe_fallback", "no_evidence", "clarification"] | None = None
    answer: AnswerV1 | None = None
    sources: list[SourceV1]
    coverage: CoverageV1
    graph_url: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    error_code: str | None = None


class EvidenceV1(StrictModel):
    evidence_id: UUID
    document_id: UUID
    revision_id: UUID
    chunk_id: UUID
    section: str
    span_start: int = Field(ge=0)
    span_end: int = Field(ge=0)
    quoted_span: str
    source_url: str
