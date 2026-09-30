"""Общие DTO версии v1; бизнес-правила и хранение определены в других модулях."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QuoteV1(StrictModel):
    evidence_id: UUID
    start: int = Field(strict=True, ge=0)
    end: int = Field(strict=True, ge=0)
    text: str

    @model_validator(mode="after")
    def non_empty_span(self) -> QuoteV1:
        if self.end <= self.start or not self.text:
            raise ValueError("INVALID_QUOTE_SPAN")
        return self


class ClaimV1(StrictModel):
    text: str = Field(min_length=1, max_length=4000)
    evidence_ids: list[UUID] = Field(min_length=1, max_length=64)
    quotes: list[QuoteV1] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def evidence_matches_quotes(self) -> ClaimV1:
        cited = set(self.evidence_ids)
        quoted = {quote.evidence_id for quote in self.quotes}
        if len(cited) != len(self.evidence_ids) or not quoted <= cited:
            raise ValueError("INVALID_CLAIM_EVIDENCE_IDS")
        return self


class MatchV1(StrictModel):
    feature_id: UUID
    document_id: UUID
    claims: list[ClaimV1]


class DifferenceV1(StrictModel):
    feature_id: UUID
    claims: list[ClaimV1]


class AnalysisRelationV1(StrictModel):
    feature_id: UUID
    document_id: UUID
    relation: Literal["full", "partial", "conflicting", "uncertain"]
    evidence_ids: list[UUID] = Field(min_length=1, max_length=64)
    quotes: list[QuoteV1] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def evidence_matches_quotes(self) -> AnalysisRelationV1:
        cited = set(self.evidence_ids)
        quoted = {quote.evidence_id for quote in self.quotes}
        if len(cited) != len(self.evidence_ids) or not quoted <= cited:
            raise ValueError("INVALID_RELATION_EVIDENCE_IDS")
        return self


class AnalysisV1(StrictModel):
    """Private structured model draft, validated against the selected snapshot."""

    schema_version: Literal[1]
    relations: list[AnalysisRelationV1] = Field(max_length=960)
    unresolved_feature_ids: list[UUID] = Field(max_length=64)

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_schema_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("INVALID_SCHEMA_VERSION")
        return value

    @model_validator(mode="after")
    def unique_features(self) -> AnalysisV1:
        if len(set(self.unresolved_feature_ids)) != len(self.unresolved_feature_ids):
            raise ValueError("DUPLICATE_UNRESOLVED_FEATURE_ID")
        pairs = [(item.feature_id, item.document_id) for item in self.relations]
        if len(set(pairs)) != len(pairs):
            raise ValueError("DUPLICATE_FEATURE_DOCUMENT_RELATION")
        return self


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


class PublicAnalysisV1(StrictModel):
    schema_version: Literal[1] = 1
    items: list[ClaimV1] = Field(max_length=12)
    limitations: list[LimitationV1] = Field(max_length=16)


class AnswerPresentationV1(StrictModel):
    schema_version: Literal[1] = 1
    presentation_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    renderer_version: str = Field(min_length=1, max_length=64)
    text: str = Field(max_length=65536)
    text_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    chunk_count: int = Field(ge=1, le=128)


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
