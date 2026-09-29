"""Проверки нормализации и транзакционного ingestion для EPO/OpenAlex."""

import os
from datetime import date
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.domain.documents import DocumentSection, NormalizedDocument
from app.domain.source import FieldStatus, PatentDocument, ScientificWork
from app.services.ingestion import IngestionService, canonical_external_id
from app.storage.models import (
    DocumentRevision,
    EvidenceChunk,
    IndexCatalog,
    IndexMember,
    OutboxEvent,
    SourceDocument,
)
from app.workers.ingest import IngestionWorker

pytestmark = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="no PostgreSQL test DB")


@pytest.fixture
def engine():  # type: ignore[no-untyped-def]
    url = os.environ["TEST_DATABASE_URL"]
    admin = create_engine(url)
    schema = f"ingest_test_{uuid4().hex}"
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped_url = url + ("&" if "?" in url else "?") + f"options=-csearch_path%3D{schema}"
    scoped = create_engine(scoped_url)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", scoped_url.replace("%", "%%"))
    try:
        command.upgrade(config, "head")
        yield scoped
    finally:
        scoped.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def _patent(abstract: str = "A device with a rotating blade.") -> PatentDocument:
    return PatentDocument(
        source="epo_ops",
        external_id="EP.1234567.A1",
        country="EP",
        publication_number="1234567",
        kind="A1",
        source_url="https://worldwide.espacenet.com/patent/example",
        title="Rotating device",
        abstract=abstract,
        publication_date=date(2024, 1, 2),
        claims="1. The device comprises a blade.",
        description="Detailed description.",
        field_status={"abstract": FieldStatus.AVAILABLE, "claims": FieldStatus.AVAILABLE},
    )


def _work(abstract: str = "A study of useful materials.") -> ScientificWork:
    return ScientificWork(
        source="openalex",
        external_id="W123456789",
        source_url="https://openalex.org/W123456789",
        title="Materials study",
        abstract=abstract,
        publication_date=date(2023, 3, 4),
        updated_at=None,
        doi="https://doi.org/10.1234/example",
        landing_page_url="https://publisher.example/article",
        language="en",
        authors=(),
        topics=(),
        referenced_work_ids=(),
        cited_by_count=0,
        field_status={"abstract": FieldStatus.AVAILABLE},
    )


def test_canonical_ids_and_chunk_offsets_preserve_source_sections(engine) -> None:  # type: ignore[no-untyped-def]
    assert canonical_external_id("epo_ops", "EP.1234567.A1") == "EP1234567A1"
    assert canonical_external_id("openalex", "https://openalex.org/w123") == "W123"
    with Session(engine) as session, session.begin():
        worker = IngestionWorker(session, chunk_size=100)
        patent_revision, created = worker.ingest_epo(_patent())
        assert created
        chunks = list(
            session.scalars(
                select(EvidenceChunk)
                .where(EvidenceChunk.revision_id == patent_revision.id)
                .order_by(EvidenceChunk.section, EvidenceChunk.ordinal)
            )
        )
        sections = patent_revision.normalized_json["sections"]
        section_text = {item["name"]: item["text"] for item in sections}
        assert {chunk.section for chunk in chunks} == {"abstract", "claims", "description"}
        for chunk in chunks:
            original = section_text[chunk.section]
            assert chunk.text == original[chunk.section_start : chunk.section_end]
        assert patent_revision.normalized_json["metadata"]["field_status"]["claims"] == "available"
        work_revision, _ = worker.ingest_openalex(_work())
        abstract = next(
            chunk
            for chunk in session.scalars(
                select(EvidenceChunk).where(EvidenceChunk.revision_id == work_revision.id)
            )
        )
        assert abstract.section == "abstract"
        assert abstract.language == "en"
        assert work_revision.normalized_json["metadata"]["doi"] == "https://doi.org/10.1234/example"


def test_idempotence_changed_revision_outbox_and_index_activation_barrier(engine) -> None:  # type: ignore[no-untyped-def]
    with Session(engine) as session, session.begin():
        worker = IngestionWorker(session)
        first, created = worker.ingest_epo(_patent())
        assert created
        repeated, created = worker.ingest_epo(_patent())
        assert not created and repeated.id == first.id
        changed, created = worker.ingest_epo(_patent("A device with two rotating blades."))
        assert created and changed.id != first.id
        source = session.scalar(
            select(SourceDocument).where(SourceDocument.external_id == "EP1234567A1")
        )
        assert source is not None
        assert source.active_revision_id is None
        assert len(list(session.scalars(select(DocumentRevision)))) == 2
        assert len(list(session.scalars(select(OutboxEvent)))) == 2

        expected = {
            "qdrant": ("idx-v1", "projection-v1"),
            "domain_graph": ("idx-v1", "projection-v1"),
        }
        assert not worker.acknowledge(
            changed.id,
            backend="qdrant",
            indexer_version="idx-v1",
            projection_version="projection-v1",
            expected_versions=expected,
        )
        assert not worker.acknowledge(
            changed.id,
            backend="domain_graph",
            indexer_version="idx-v2",
            projection_version="projection-v1",
            expected_versions=expected,
        )
        # Graph ACK exists but does not match the caller's expected version pair.
        assert not worker.acknowledge(
            changed.id,
            backend="qdrant",
            indexer_version="idx-v1",
            projection_version="projection-v1",
            expected_versions=expected,
        )
        assert worker.acknowledge(
            changed.id,
            backend="domain_graph",
            indexer_version="idx-v1",
            projection_version="projection-v1",
            expected_versions=expected,
        )
        source = session.get(SourceDocument, source.id)
        assert source is not None and source.active_revision_id == changed.id
        members = list(session.scalars(select(IndexMember)))
        assert len(members) == 1 and members[0].revision_id == changed.id
        catalog = session.get(IndexCatalog, 1)
        assert catalog is not None and catalog.current_generation_id == members[0].generation_id


def test_invalid_payload_does_not_leave_partial_rows(engine) -> None:  # type: ignore[no-untyped-def]
    with Session(engine) as session:
        invalid = NormalizedDocument(
            source="openalex",
            external_id="W999",
            canonical_url="https://openalex.org/W999",
            kind="article",
            title="Invalid serialization",
            publication_date=None,
            source_updated_at=None,
            sections=(DocumentSection("abstract", "Some text.", "en"),),
            metadata={"unsupported": object()},
        )
        with pytest.raises(TypeError):
            IngestionService(session).ingest(invalid)
        session.rollback()
        assert session.scalar(select(SourceDocument)) is None
        assert session.scalar(select(DocumentRevision)) is None
