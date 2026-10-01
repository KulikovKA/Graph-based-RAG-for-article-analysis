"""Независимые от хранилища контракты результатов внешних источников."""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum


class SourceStatus(StrEnum):
    OK = "ok"
    EMPTY = "empty"
    NOT_CONFIGURED = "not_configured"
    UNAVAILABLE = "unavailable"


class FieldStatus(StrEnum):
    AVAILABLE = "available"
    MISSING = "missing"
    NOT_REQUESTED = "not_requested"


@dataclass(frozen=True)
class PatentDocument:
    source: str
    external_id: str
    country: str
    publication_number: str
    kind: str
    source_url: str
    title: str | None
    abstract: str | None
    publication_date: date | None
    claims: str | None = None
    description: str | None = None
    field_status: dict[str, FieldStatus] = field(default_factory=dict)


@dataclass(frozen=True)
class PatentResult:
    status: SourceStatus
    documents: tuple[PatentDocument, ...] = ()
    error_code: str | None = None
    retry_after_seconds: float | None = None
    next_offset: int | None = None
    total_count: int | None = None


@dataclass(frozen=True)
class WorkAuthor:
    id: str | None
    name: str | None


@dataclass(frozen=True)
class WorkTopic:
    id: str | None
    name: str | None
    score: float | None


@dataclass(frozen=True)
class ScientificWork:
    source: str
    external_id: str
    source_url: str
    title: str | None
    abstract: str | None
    publication_date: date | None
    updated_at: datetime | None
    doi: str | None
    landing_page_url: str | None
    language: str | None
    authors: tuple[WorkAuthor, ...]
    topics: tuple[WorkTopic, ...]
    referenced_work_ids: tuple[str, ...]
    cited_by_count: int | None
    field_status: dict[str, FieldStatus] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkResult:
    status: SourceStatus
    works: tuple[ScientificWork, ...] = ()
    next_cursor: str | None = None
    total_count: int | None = None
    error_code: str | None = None
    retry_after_seconds: float | None = None
