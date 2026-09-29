"""Каноническая модель публичного документа и его индексируемых разделов."""

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class DocumentSection:
    name: str
    text: str
    language: str | None = None


@dataclass(frozen=True)
class NormalizedDocument:
    source: str
    external_id: str
    canonical_url: str
    kind: str
    title: str
    publication_date: date | None
    source_updated_at: datetime | None
    sections: tuple[DocumentSection, ...]
    metadata: dict[str, object]
