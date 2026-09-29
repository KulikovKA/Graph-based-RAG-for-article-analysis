"""Граница worker-а ingestion: адаптерный DTO → единый сервис записи."""

from datetime import UTC
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.documents import DocumentSection, NormalizedDocument
from app.domain.source import PatentDocument, ScientificWork
from app.services.ingestion import IngestionService
from app.storage.models import DocumentRevision


def from_epo(document: PatentDocument) -> NormalizedDocument:
    sections = tuple(
        DocumentSection(name=name, text=value)
        for name, value in (
            ("abstract", document.abstract),
            ("claims", document.claims),
            ("description", document.description),
        )
        if value
    )
    return NormalizedDocument(
        source="epo_ops",
        external_id=document.external_id,
        canonical_url=document.source_url,
        kind="patent",
        title=document.title or document.external_id,
        publication_date=document.publication_date,
        source_updated_at=None,
        sections=sections,
        metadata={
            "country": document.country,
            "publication_number": document.publication_number,
            "kind_code": document.kind,
            "field_status": {key: value.value for key, value in document.field_status.items()},
        },
    )


def from_openalex(work: ScientificWork) -> NormalizedDocument:
    sections = (DocumentSection("abstract", work.abstract, work.language),) if work.abstract else ()
    return NormalizedDocument(
        source="openalex",
        external_id=work.external_id,
        canonical_url=work.source_url,
        kind="article",
        title=work.title or work.external_id,
        publication_date=work.publication_date,
        source_updated_at=(
            work.updated_at.astimezone(UTC)
            if work.updated_at and work.updated_at.tzinfo
            else work.updated_at
        ),
        sections=sections,
        metadata={
            "doi": work.doi,
            "landing_page_url": work.landing_page_url,
            "language": work.language,
            "authors": [{"id": author.id, "name": author.name} for author in work.authors],
            "topics": [
                {"id": topic.id, "name": topic.name, "score": topic.score} for topic in work.topics
            ],
            "referenced_work_ids": list(work.referenced_work_ids),
            "cited_by_count": work.cited_by_count,
            "field_status": {key: value.value for key, value in work.field_status.items()},
        },
    )


class IngestionWorker:
    """Адаптер для обработки нормализованных записей в транзакции caller-а."""

    def __init__(self, session: Session, *, chunk_size: int = 1200) -> None:
        self.service = IngestionService(session, chunk_size=chunk_size)

    def ingest_epo(self, document: PatentDocument) -> tuple[DocumentRevision, bool]:
        return self.service.ingest(from_epo(document))

    def ingest_openalex(self, work: ScientificWork) -> tuple[DocumentRevision, bool]:
        return self.service.ingest(from_openalex(work))

    def acknowledge(
        self,
        revision_id: UUID,
        *,
        backend: str,
        indexer_version: str,
        projection_version: str,
        expected_versions: dict[str, tuple[str, str]],
    ) -> bool:
        return self.service.acknowledge(
            revision_id,
            backend=backend,
            indexer_version=indexer_version,
            projection_version=projection_version,
            expected_versions=expected_versions,
        )
