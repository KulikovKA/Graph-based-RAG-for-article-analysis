"""PostgreSQL backed RET contract checks with isolated Qdrant/graph responses."""

import asyncio
import base64
import os
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.domain.graph import GraphEdgeType
from app.domain.planner import FeatureV1, IdeaV1
from app.integrations.neo4j import GraphEdgeRecord
from app.integrations.qdrant import VectorHit
from app.services.retrieval import CandidateRetrievalService, RetrievalConfig
from app.storage.models import (
    DocumentRevision,
    EvidenceChunk,
    GraphFact,
    IndexGeneration,
    IndexMember,
    SourceDocument,
    utcnow,
)
from app.storage.repositories import make_session_factory

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is required"
)


class FakeEmbedder:
    async def embed(self, *, model_id: str, request_id: str, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


class FakeQdrant:
    def __init__(self, hits: list[VectorHit]) -> None:
        self.spec = SimpleNamespace(model_id="fixture", projection_version="fixture-v1")
        self.hits = hits

    async def query(
        self,
        vector: list[float],
        *,
        limit: int,
        offset: int = 0,
        source: str | None = None,
        source_id: str | None = None,
        section: str | None = None,
        language: str | None = None,
        document_ids: list[UUID] | None = None,
    ) -> list[VectorHit]:
        return self.hits[offset : offset + limit]


class FakeGraph:
    def __init__(self, records: list[GraphEdgeRecord]) -> None:
        self.records = records

    async def one_hop(self, key: str, *, limit: int = 50) -> list[GraphEdgeRecord]:
        return [record for record in self.records if key == record.target_key][:limit]


def _feature_key(text_value: str) -> str:
    canonical = " ".join(text_value.casefold().split())
    encoded = base64.urlsafe_b64encode(canonical.encode()).decode().rstrip("=")
    return f"retrieval-test:feature:technical-feature-v1:{encoded}"


def test_channels_resolve_only_members_of_pinned_generation() -> None:
    async def exercise() -> None:
        database_url = os.environ["TEST_DATABASE_URL"]
        admin = create_engine(database_url)
        schema = f"retrieval_test_{uuid4().hex}"
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        scoped_url = database_url + ("&" if "?" in database_url else "?") + (
            f"options=-csearch_path%3D{schema}"
        )
        engine = create_engine(scoped_url)
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", scoped_url.replace("%", "%%"))
        try:
            command.upgrade(config, "head")
            generation_id = uuid4()
            valid_document_id, inactive_document_id, private_document_id = (
                uuid4(), uuid4(), uuid4()
            )
            valid_revision_id, inactive_revision_id, private_revision_id = (
                uuid4(), uuid4(), uuid4()
            )
            valid_chunk_id, inactive_chunk_id, private_chunk_id = uuid4(), uuid4(), uuid4()
            fact_ids = (uuid4(), uuid4(), uuid4())
            target_key = _feature_key("thermal storage")
            with Session(engine) as session, session.begin():
                generation = IndexGeneration(
                    id=generation_id,
                    config_versions_json={"qdrant": {"projection_version": "fixture-v1"}},
                )
                session.add(generation)
                documents = [
                    SourceDocument(
                        id=valid_document_id,
                        source="openalex",
                        external_id="W1234567890",
                        canonical_url="https://openalex.org/W1234567890",
                        kind="article",
                        title="Thermal storage system",
                    ),
                    SourceDocument(
                        id=inactive_document_id,
                        source="openalex",
                        external_id="W1234567891",
                        canonical_url="https://openalex.org/W1234567891",
                        kind="article",
                        title="Thermal storage inactive revision",
                    ),
                    SourceDocument(
                        id=private_document_id,
                        source="private",
                        external_id="PRIVATE-1",
                        canonical_url="https://private.example/thermal-storage",
                        kind="article",
                        title="Thermal storage private record",
                    ),
                ]
                session.add_all(documents)
                session.flush()
                revisions = [
                    DocumentRevision(
                        id=revision_id,
                        document_id=document_id,
                        content_hash=f"{index:064x}",
                        normalized_json={"source": "openalex"},
                        ingest_state="indexed",
                    )
                    for index, (revision_id, document_id) in enumerate(
                        (
                            (valid_revision_id, valid_document_id),
                            (inactive_revision_id, inactive_document_id),
                            (private_revision_id, private_document_id),
                        ),
                        start=1,
                    )
                ]
                session.add_all(revisions)
                chunks = [
                    EvidenceChunk(
                        id=chunk_id,
                        revision_id=revision_id,
                        section="abstract",
                        ordinal=0,
                        text=chunk_text,
                        section_start=0,
                        section_end=len(chunk_text),
                        hash=f"{index:064x}",
                        language="en",
                    )
                    for index, (chunk_id, revision_id, chunk_text) in enumerate(
                        (
                            (valid_chunk_id, valid_revision_id,
                             "Thermal storage captures heat for later use."),
                            (inactive_chunk_id, inactive_revision_id,
                             "Thermal storage captures heat in an inactive revision."),
                            (private_chunk_id, private_revision_id,
                             "Thermal storage captures heat in a private record."),
                        ),
                        start=3,
                    )
                ]
                session.add_all(chunks)
                session.add(
                    IndexMember(
                        generation_id=generation_id,
                        document_id=valid_document_id,
                        revision_id=valid_revision_id,
                    )
                )
                session.add(
                    IndexMember(
                        generation_id=generation_id,
                        document_id=private_document_id,
                        revision_id=private_revision_id,
                    )
                )
                for index, (fact_id, revision_id, chunk_id, document_id) in enumerate(
                    (
                        (fact_ids[0], valid_revision_id, valid_chunk_id, valid_document_id),
                        (fact_ids[1], inactive_revision_id, inactive_chunk_id,
                         inactive_document_id),
                        (fact_ids[2], private_revision_id, private_chunk_id, private_document_id),
                    ),
                    start=1,
                ):
                    session.add(
                        GraphFact(
                            id=fact_id,
                            revision_id=revision_id,
                            from_key=f"retrieval-test:work:{document_id}:rev:{revision_id}",
                            edge_type=GraphEdgeType.DISCLOSES_FEATURE.value,
                            to_key=target_key,
                            chunk_id=chunk_id,
                            span_start=0,
                            span_end=15,
                            provenance_key=f"chunk:{chunk_id}:0:15",
                            logical_key_hash=f"{index + 8:064x}",
                            provenance_kind="abstract",
                            extractor_version="fixture-v1",
                            vocabulary_version="technical-feature-v1",
                            confidence=0.9,
                            validated_at=utcnow(),
                        )
                    )

            graph_records = [
                GraphEdgeRecord(
                    source_key=f"retrieval-test:work:{document_id}:rev:{revision_id}",
                    source_label="ScientificWork",
                    edge_type=GraphEdgeType.DISCLOSES_FEATURE.value,
                    target_key=target_key,
                    target_label="TechnicalFeature",
                    properties={"fact_id": str(fact_id)},
                )
                for fact_id, revision_id, document_id in (
                    (fact_ids[0], valid_revision_id, valid_document_id),
                    (fact_ids[1], inactive_revision_id, inactive_document_id),
                    (fact_ids[2], private_revision_id, private_document_id),
                )
            ]
            service = CandidateRetrievalService(
                make_session_factory(engine),
                FakeQdrant(
                    [
                        VectorHit(valid_chunk_id, valid_document_id, valid_revision_id, 0.9),
                        VectorHit(
                            inactive_chunk_id, inactive_document_id, inactive_revision_id, 0.99
                        ),
                        VectorHit(private_chunk_id, private_document_id, private_revision_id, 0.98),
                    ]
                ),
                FakeEmbedder(),
                FakeGraph(graph_records),  # type: ignore[arg-type]
                graph_namespace="retrieval-test",
                graph_vocabulary_version="technical-feature-v1",
                config=RetrievalConfig(total_limit=10),
            )
            result = await service.search(
                original_query="thermal storage",
                idea=IdeaV1(
                    domain="energy",
                    features=[FeatureV1(id=uuid4(), text="thermal storage")],
                    language="en",
                ),
                generation_id=generation_id,
                request_id="retrieval-test",
            )
            assert result.query.subqueries[0].text == "thermal storage"
            assert result.coverage.partial is False
            assert {item.document_id for item in result.candidates} == {valid_document_id}
            assert set(result.candidates[0].channels) == {"qdrant", "metadata", "domain_graph"}
        finally:
            engine.dispose()
            with admin.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            admin.dispose()

    asyncio.run(exercise())
