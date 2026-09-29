"""Нормализация, дедупликация и атомарная запись документов в PostgreSQL."""

import hashlib
import json
import re
from datetime import UTC
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.domain.documents import DocumentSection, NormalizedDocument
from app.storage.jobs import OutboxRepository
from app.storage.models import (
    DocumentRevision,
    EvidenceChunk,
    IndexCatalog,
    IndexGeneration,
    IndexMember,
    IngestionJob,
    RevisionIndexAck,
    SourceDocument,
)

_SOURCES = {"epo_ops", "openalex"}
_REQUIRED_BACKENDS = {"qdrant", "domain_graph"}
_LANGUAGE_RE = re.compile(r"^[a-z]{2,3}(?:-[a-z0-9]{2,8})*$", re.IGNORECASE)


def canonical_external_id(source: str, external_id: str) -> str:
    """Вернуть стабильный внешний ключ для поддерживаемых источников."""
    value = external_id.strip()
    if source == "epo_ops":
        value = re.sub(r"[\s.]", "", value).upper()
        if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]+[A-Z][0-9]?", value):
            raise ValueError("invalid EPO publication ID")
        return value
    if source == "openalex":
        value = value.rsplit("/", 1)[-1].upper()
        if not re.fullmatch(r"W[0-9]+", value):
            raise ValueError("invalid OpenAlex work ID")
        return value
    raise ValueError("unsupported source")


def _language(value: str | None, text: str) -> str:
    if value and _LANGUAGE_RE.fullmatch(value):
        return value.lower()
    letters = [char for char in text if char.isalpha()]
    if letters and sum("\u0400" <= char <= "\u04ff" for char in letters) / len(letters) > 0.25:
        return "ru"
    return "und"


def _split_points(text: str, language: str) -> list[tuple[int, int]]:
    """Разбить по абзацам/предложениям, затем ограничить длинные предложения пробелами."""
    points: list[tuple[int, int]] = []
    endings = ".!?。！？؟" if language.split("-", 1)[0] in {"zh", "ja", "ko", "ar"} else ".!?"
    boundaries = re.finditer(rf"(?<=[{re.escape(endings)}])(?=\s)|\n+", text)
    start = 0
    for boundary in boundaries:
        left, right = start, boundary.start()
        while left < right and text[left].isspace():
            left += 1
        while right > left and text[right - 1].isspace():
            right -= 1
        if right > left:
            points.append((left, right))
        start = boundary.end()
    left, right = start, len(text)
    while left < right and text[left].isspace():
        left += 1
    while right > left and text[right - 1].isspace():
        right -= 1
    if right > left:
        points.append((left, right))
    return points


def _pieces(text: str, limit: int, language: str) -> list[tuple[int, int]]:
    output: list[tuple[int, int]] = []
    for left, right in _split_points(text, language):
        while right - left > limit:
            boundary = text.rfind(" ", left, left + limit + 1)
            if boundary <= left:
                boundary = left + limit
            output.append((left, boundary))
            left = boundary
            while left < right and text[left].isspace():
                left += 1
        if left < right:
            output.append((left, right))
    return output


def _chunks(sections: tuple[DocumentSection, ...], limit: int) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for section in sections:
        if not section.name.strip() or not section.text.strip():
            continue
        section_text = section.text
        language = _language(section.language, section_text)
        ordinal = 0
        pending: tuple[int, int] | None = None
        for start, end in _pieces(section_text, limit, language):
            if pending and start - pending[0] <= limit:
                combined = (pending[0], end)
                # Keep adjacent short sentences together while preserving exact source offsets.
                if end - pending[0] <= limit:
                    pending = combined
                    continue
                result.append(_chunk_row(section.name, ordinal, section_text, *pending, language))
                ordinal += 1
            pending = (start, end)
        if pending:
            result.append(_chunk_row(section.name, ordinal, section_text, *pending, language))
    return result


def _chunk_row(
    section: str, ordinal: int, source: str, start: int, end: int, language: str
) -> dict[str, Any]:
    value = source[start:end]
    return {
        "section": section,
        "ordinal": ordinal,
        "text": value,
        "section_start": start,
        "section_end": end,
        "hash": hashlib.sha256(value.encode("utf-8")).hexdigest(),
        "language": language,
    }


def chunk_sections(
    sections: tuple[DocumentSection, ...], chunk_size: int = 1200
) -> list[dict[str, Any]]:
    """Разбить разделы с точными полуинтервалами Unicode offsets."""
    if chunk_size < 100 or chunk_size > 10000:
        raise ValueError("chunk_size must be between 100 and 10000")
    return _chunks(sections, chunk_size)


def _payload(document: NormalizedDocument, external_id: str) -> dict[str, Any]:
    return {
        "source": document.source,
        "external_id": external_id,
        "canonical_url": document.canonical_url,
        "kind": document.kind,
        "title": document.title.strip(),
        "publication_date": (
            document.publication_date.isoformat() if document.publication_date else None
        ),
        "source_updated_at": (
            document.source_updated_at.astimezone(UTC).isoformat()
            if document.source_updated_at
            else None
        ),
        "sections": [
            {"name": item.name, "text": item.text, "language": item.language}
            for item in document.sections
        ],
        "metadata": document.metadata,
    }


class IngestionService:
    """Запись одной полной source payload в транзакции вызывающего кода."""

    def __init__(self, session: Session, *, chunk_size: int = 1200) -> None:
        if chunk_size < 100 or chunk_size > 10000:
            raise ValueError("chunk_size must be between 100 and 10000")
        self.session = session
        self.chunk_size = chunk_size

    def ingest(self, document: NormalizedDocument) -> tuple[DocumentRevision, bool]:
        if document.source not in _SOURCES:
            raise ValueError("unsupported source")
        external_id = canonical_external_id(document.source, document.external_id)
        if not document.title.strip() or not document.kind.strip():
            raise ValueError("document title and kind are required")
        parsed_url = re.fullmatch(r"https://[^\s]+", document.canonical_url)
        if not parsed_url:
            raise ValueError("canonical URL must use HTTPS")
        canonical = _payload(document, external_id)
        content_hash = hashlib.sha256(
            json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()

        source = self.session.scalar(
            select(SourceDocument)
            .where(
                SourceDocument.source == document.source,
                SourceDocument.external_id == external_id,
            )
            .with_for_update()
        )
        if source is None:
            self.session.execute(
                insert(SourceDocument)
                .values(
                    source=document.source,
                    external_id=external_id,
                    canonical_url=document.canonical_url,
                    kind=document.kind[:32],
                    title=document.title.strip(),
                    publication_date=document.publication_date,
                )
                .on_conflict_do_nothing(index_elements=["source", "external_id"])
            )
            source = self.session.scalar(
                select(SourceDocument)
                .where(
                    SourceDocument.source == document.source,
                    SourceDocument.external_id == external_id,
                )
                .with_for_update()
            )
            assert source is not None
        else:
            source.canonical_url = document.canonical_url
            source.kind = document.kind[:32]
            source.title = document.title.strip()
            source.publication_date = document.publication_date
        existing = self.session.scalar(
            select(DocumentRevision).where(
                DocumentRevision.document_id == source.id,
                DocumentRevision.content_hash == content_hash,
            )
        )
        job = self.session.scalar(
            select(IngestionJob).where(
                IngestionJob.source == document.source,
                IngestionJob.external_id == external_id,
                IngestionJob.payload_hash == content_hash,
            )
        )
        if job is None:
            job = IngestionJob(
                source=document.source,
                external_id=external_id,
                payload_hash=content_hash,
                status="completed" if existing else "pending",
            )
            self.session.add(job)
            self.session.flush()
        if existing is not None:
            return existing, False

        revision = DocumentRevision(
            document_id=source.id,
            source_updated_at=document.source_updated_at,
            content_hash=content_hash,
            normalized_json=canonical,
            ingest_state="normalized",
        )
        self.session.add(revision)
        self.session.flush()
        for row in _chunks(document.sections, self.chunk_size):
            self.session.add(EvidenceChunk(revision_id=revision.id, **row))
        OutboxRepository(self.session).enqueue(
            aggregate_id=revision.id,
            kind="revision.ready",
            payload={"revision_id": str(revision.id), "content_hash": content_hash},
        )
        job.status = "completed"
        job.error_code = None
        self.session.flush()
        return revision, True

    def acknowledge(
        self,
        revision_id: UUID,
        *,
        backend: str,
        indexer_version: str,
        projection_version: str,
        expected_versions: dict[str, tuple[str, str]],
    ) -> bool:
        """Сохранить ACK; активировать лишь при точных версиях обоих обязательных индексов."""
        if backend not in _REQUIRED_BACKENDS:
            raise ValueError("unsupported required backend")
        if not indexer_version or not projection_version:
            raise ValueError("ACK versions are required")
        if set(expected_versions) != _REQUIRED_BACKENDS or any(
            not indexer or not projection
            for indexer, projection in expected_versions.values()
        ):
            raise ValueError("expected versions for both required backends are required")
        revision = self.session.scalar(
            select(DocumentRevision).where(DocumentRevision.id == revision_id).with_for_update()
        )
        if revision is None:
            raise LookupError("revision not found")
        self.session.execute(
            insert(RevisionIndexAck)
            .values(
                revision_id=revision_id,
                backend=backend,
                indexer_version=indexer_version,
                projection_version=projection_version,
            )
            .on_conflict_do_nothing(
                index_elements=["revision_id", "backend", "indexer_version", "projection_version"]
            )
        )
        acks = list(
            self.session.scalars(
                select(RevisionIndexAck).where(
                    RevisionIndexAck.revision_id == revision_id,
                    RevisionIndexAck.backend.in_(_REQUIRED_BACKENDS),
                )
            )
        )
        by_backend = {}
        for backend_name in _REQUIRED_BACKENDS:
            expected = expected_versions[backend_name]
            ack = next(
                (
                    item
                    for item in acks
                    if item.backend == backend_name
                    and (item.indexer_version, item.projection_version) == expected
                ),
                None,
            )
            if ack is None:
                return False
            by_backend[backend_name] = ack
        if revision.ingest_state == "indexed":
            return True
        source = self.session.scalar(
            select(SourceDocument)
            .where(SourceDocument.id == revision.document_id)
            .with_for_update()
        )
        assert source is not None
        self.session.execute(
            insert(IndexCatalog).values(id=1).on_conflict_do_nothing(index_elements=["id"])
        )
        catalog = self.session.scalar(
            select(IndexCatalog).where(IndexCatalog.id == 1).with_for_update()
        )
        if catalog is None:
            raise RuntimeError("index catalog row was not initialized")
        generation = IndexGeneration(
            parent_id=catalog.current_generation_id,
            config_versions_json={
                backend_name: {
                    "indexer_version": versions[0],
                    "projection_version": versions[1],
                }
                for backend_name, versions in expected_versions.items()
            },
        )
        self.session.add(generation)
        self.session.flush()
        if catalog.current_generation_id is not None:
            previous = list(
                self.session.scalars(
                    select(IndexMember).where(
                        IndexMember.generation_id == catalog.current_generation_id
                    )
                )
            )
            self.session.add_all(
                IndexMember(
                    generation_id=generation.id,
                    document_id=item.document_id,
                    revision_id=item.revision_id,
                )
                for item in previous
                if item.document_id != source.id
            )
        self.session.add(
            IndexMember(generation_id=generation.id, document_id=source.id, revision_id=revision.id)
        )
        source.active_revision_id = revision.id
        catalog.current_generation_id = generation.id
        revision.ingest_state = "indexed"
        self.session.flush()
        return True
