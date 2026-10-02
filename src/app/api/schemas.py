"""Публичные DTO: входы и allowlist сохранённых SSE payloads."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.domain.contracts import (
    CoverageV1,
    ProgressV1,
    PublicAnalysisV1,
    RunV1,
    SourceV1,
    StrictModel,
)


class ConversationInput(StrictModel):
    title: str | None = Field(default=None, max_length=512)


class MessageInput(StrictModel):
    content: str = Field(min_length=1, max_length=8192)
    expected_idea_version: int = Field(strict=True, ge=0)
    source_run_id: UUID | None = None
    analyze: Literal[True]

    @field_validator("content")
    @classmethod
    def content_bytes(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("EMPTY_CONTENT")
        if len(value.encode("utf-8")) > 8192:
            raise ValueError("CONTENT_TOO_LARGE")
        return value


class ConversationV1(StrictModel):
    id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


class MessageV1(StrictModel):
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    run_id: UUID | None
    created_at: datetime


class AcceptedV1(StrictModel):
    message_id: UUID
    run_id: UUID
    status_url: str
    events_url: str


class ProgressPayload(StrictModel):
    schema_version: Literal[1]
    progress: ProgressV1


class IdeaPayload(ProgressPayload):
    idea_version_id: UUID


class RequeuePayload(ProgressPayload):
    reason_code: str


class SourcesPayload(StrictModel):
    schema_version: Literal[1]
    sources: list[SourceV1]
    coverage: CoverageV1


class VerificationPayload(StrictModel):
    schema_version: Literal[1]
    phase: Literal["started", "completed"]
    scope: Literal["analysis", "result"]
    attempt: int | None = None
    outcome: Literal["analysis", "safe_fallback", "no_evidence", "clarification"] | None = None


class SummaryPayload(StrictModel):
    schema_version: Literal[1]
    public_analysis: PublicAnalysisV1


class AnswerStartedPayload(StrictModel):
    schema_version: Literal[1]
    presentation_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    renderer_version: str
    chunk_count: int = Field(ge=1, le=128)
    text_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class DeltaPayload(StrictModel):
    schema_version: Literal[1]
    presentation_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    chunk_index: int = Field(ge=0, lt=128)
    text: str = Field(max_length=1024)


class TerminalPayload(StrictModel):
    schema_version: Literal[1]
    run: RunV1


class ResetPayload(TerminalPayload):
    high_water: int = Field(ge=0)
    reset: Literal[True]


EVENT_SCHEMAS: dict[str, type[StrictModel]] = {
    **{
        name: ProgressPayload
        for name in ("run_started", "planning", "retrieving", "reranking", "analyzing")
    },
    "idea_updated": IdeaPayload,
    "run_requeued": RequeuePayload,
    "sources_ready": SourcesPayload,
    "verification": VerificationPayload,
    "analysis_summary": SummaryPayload,
    "answer_started": AnswerStartedPayload,
    "answer_delta": DeltaPayload,
    "completed": TerminalPayload,
    "failed": TerminalPayload,
    "cancelled": TerminalPayload,
    "run_snapshot": ResetPayload,
}
