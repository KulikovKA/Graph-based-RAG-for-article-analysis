"""Независимый от хранилища контракт результата поиска патентов."""

from dataclasses import dataclass, field
from datetime import date
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
