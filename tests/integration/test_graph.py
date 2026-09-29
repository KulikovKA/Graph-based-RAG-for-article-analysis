"""Интеграционные тесты проекции и восстановления PostgreSQL/Neo4j."""

import asyncio
import os
from uuid import uuid4

import httpx
import pytest
from alembic import command
from alembic.config import Config
from neo4j import AsyncGraphDatabase
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.domain.documents import DocumentSection, NormalizedDocument
from app.integrations.neo4j import PROJECTION_VERSION, Neo4jGraph
from app.integrations.qdrant import EmbeddingSpec, QdrantIndex
from app.services.graph_index import GraphChunk, GraphIndexingService
from app.services.indexing import IndexingService
from app.services.ingestion import IngestionService
from app.storage.models import EvidenceChunk, IndexCatalog, IndexGeneration, IndexMember

pytestmark = pytest.mark.skipif(
    not all(
        os.getenv(name)
        for name in (
            "TEST_DATABASE_URL",
            "TEST_QDRANT_URL",
            "TEST_NEO4J_URI",
            "TEST_NEO4J_USER",
            "TEST_NEO4J_PASSWORD",
        )
    ),
    reason="TEST_DATABASE_URL, TEST_QDRANT_URL and TEST_NEO4J_* are required",
)


class FakeEmbedder:
    async def embed(self, *, model_id: str, request_id: str, texts: list[str]) -> list[list[float]]:
        return [[float(len(value)), 1.0] for value in texts]


class FakeGraphExtractor:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def extract(self, chunks: tuple[GraphChunk, ...], *, request_id: str) -> list[object]:
        self.calls.append(request_id)
        facts: list[object] = []
        for chunk in chunks:
            start = chunk.text.casefold().find("heat pump")
            if start < 0:
                continue
            end = start + len("heat pump")
            facts.append(
                {
                    "edge_type": "DISCLOSES_FEATURE",
                    "target_label": "TechnicalFeature",
                    "target_text": "heat pump",
                    "evidence_chunk_id": str(chunk.id),
                    "span_start": start,
                    "span_end": end,
                    "quote": chunk.text[start:end],
                    "confidence": 0.97,
                }
            )
        return facts


def _document(
    title: str, abstract: str = "A heat pump stores thermal energy."
) -> NormalizedDocument:
    return NormalizedDocument(
        source="openalex",
        external_id="W999999901",
        canonical_url="https://openalex.org/W999999901",
        kind="article",
        title=title,
        publication_date=None,
        source_updated_at=None,
        sections=(DocumentSection("abstract", abstract, "en"),),
        metadata={},
    )


def test_durable_graph_projection_recovery_revision_removal_and_ack_gate() -> None:
    async def exercise() -> None:
        database_url = os.environ["TEST_DATABASE_URL"]
        admin = create_engine(database_url)
        schema = f"graph_test_{uuid4().hex}"
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        scoped_url = database_url + ("&" if "?" in database_url else "?")
        scoped_url += f"options=-csearch_path%3D{schema}"
        engine = create_engine(scoped_url)
        session_factory = sessionmaker(engine, expire_on_commit=False, class_=Session)
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", scoped_url.replace("%", "%%"))
        namespace = f"graph_test_{uuid4().hex}"
        spec = EmbeddingSpec(namespace, "test-embedding", "v1", 2)
        driver = AsyncGraphDatabase.driver(
            os.environ["TEST_NEO4J_URI"],
            auth=(os.environ["TEST_NEO4J_USER"], os.environ["TEST_NEO4J_PASSWORD"]),
        )
        graph = Neo4jGraph(driver, namespace=namespace)
        extractor = FakeGraphExtractor()
        async with httpx.AsyncClient(
            base_url=os.environ["TEST_QDRANT_URL"], timeout=30
        ) as qdrant_client:
            qdrant = QdrantIndex(qdrant_client, spec)
            try:
                command.upgrade(config, "head")
                await driver.verify_connectivity()
                await graph.ensure_schema()
                with session_factory.begin() as session:
                    first, _ = IngestionService(session).ingest(_document("Thermal storage v1"))
                    first_id = first.id
                    first_document_id = first.document_id
                with session_factory() as session:
                    qdrant_index = IndexingService(session, qdrant, FakeEmbedder())
                    first_qdrant_count = await qdrant_index.index_revision(
                        first_id, request_id="graph-first-qdrant"
                    )
                assert first_qdrant_count == 1
                graph_index = GraphIndexingService(session_factory, graph, extractor)
                first_graph = await graph_index.index_revision(first_id, request_id="graph-first")
                assert first_graph.fact_count == 1
                assert first_graph.projection_version == PROJECTION_VERSION
                assert (
                    await graph_index.index_revision(first_id, request_id="graph-first-retry")
                    == first_graph
                )
                assert extractor.calls == ["graph-first"]

                expected = {
                    "qdrant": ("qdrant-test-v1", spec.projection_version),
                    "domain_graph": (first_graph.indexer_version, first_graph.projection_version),
                }
                with session_factory.begin() as session:
                    assert not IngestionService(session).acknowledge(
                        first_id,
                        backend="qdrant",
                        indexer_version=expected["qdrant"][0],
                        projection_version=expected["qdrant"][1],
                        expected_versions=expected,
                    )
                with session_factory() as session:
                    catalog = session.get(IndexCatalog, 1)
                    assert catalog is None or catalog.current_generation_id is None
                with session_factory.begin() as session:
                    assert IngestionService(session).acknowledge(
                        first_id,
                        backend="domain_graph",
                        indexer_version=expected["domain_graph"][0],
                        projection_version=expected["domain_graph"][1],
                        expected_versions=expected,
                    )
                with session_factory() as session:
                    catalog = session.get(IndexCatalog, 1)
                    assert catalog is not None and catalog.current_generation_id is not None
                    first_generation_id = catalog.current_generation_id
                    first_generation = session.get(IndexGeneration, first_generation_id)
                    assert first_generation is not None
                    assert (
                        first_generation.config_versions_json["domain_graph"]["projection_version"]
                        == PROJECTION_VERSION
                    )
                    assert (
                        session.scalar(
                            select(IndexMember).where(
                                IndexMember.generation_id == first_generation_id,
                                IndexMember.revision_id == first_id,
                            )
                        )
                        is not None
                    )

                first_root = f"{namespace}:work:{first_document_id}:rev:{first_id}"
                first_edges = await graph.one_hop(first_root)
                assert len(first_edges) == 1
                assert first_edges[0].edge_type == "DISCLOSES_FEATURE"
                assert first_edges[0].properties["document_revision_id"] == str(first_id)
                assert first_edges[0].properties["evidence_chunk_id"]
                assert "id" not in first_edges[0].properties
                with pytest.raises(ValueError, match="limit"):
                    await graph.one_hop(first_root, limit=101)

                # Новая ревизия хранит тот же текст, но имеет собственные chunk ID и graph key.
                with session_factory.begin() as session:
                    second, created = IngestionService(session).ingest(
                        _document("Thermal storage v2")
                    )
                assert created
                second_id = second.id
                with session_factory() as session:
                    second_chunk = session.scalar(
                        select(EvidenceChunk.id).where(EvidenceChunk.revision_id == second_id)
                    )
                    assert second_chunk is not None
                    qdrant_index = IndexingService(session, qdrant, FakeEmbedder())
                    assert (
                        await qdrant_index.index_revision(
                            second_id, request_id="graph-second-qdrant"
                        )
                        == 1
                    )
                second_graph = await graph_index.index_revision(
                    second_id, request_id="graph-second"
                )
                assert second_graph.fact_count == 1
                assert extractor.calls == ["graph-first", "graph-second"]
                second_root = f"{namespace}:work:{first_document_id}:rev:{second_id}"
                second_edges = await graph.one_hop(second_root)
                assert len(second_edges) == 1
                assert second_edges[0].properties["document_revision_id"] == str(second_id)
                assert second_edges[0].properties["evidence_chunk_id"] == str(second_chunk)
                assert (
                    second_edges[0].properties["evidence_chunk_id"]
                    != first_edges[0].properties["evidence_chunk_id"]
                )

                expected_second = {
                    "qdrant": ("qdrant-test-v1", spec.projection_version),
                    "domain_graph": (second_graph.indexer_version, second_graph.projection_version),
                }
                with session_factory.begin() as session:
                    assert not IngestionService(session).acknowledge(
                        second_id,
                        backend="qdrant",
                        indexer_version=expected_second["qdrant"][0],
                        projection_version=expected_second["qdrant"][1],
                        expected_versions=expected_second,
                    )
                with session_factory() as session:
                    catalog = session.get(IndexCatalog, 1)
                    assert catalog is not None
                    assert catalog.current_generation_id == first_generation_id
                with session_factory.begin() as session:
                    assert IngestionService(session).acknowledge(
                        second_id,
                        backend="domain_graph",
                        indexer_version=expected_second["domain_graph"][0],
                        projection_version=expected_second["domain_graph"][1],
                        expected_versions=expected_second,
                    )
                with session_factory() as session:
                    catalog = session.get(IndexCatalog, 1)
                    assert catalog is not None and catalog.current_generation_id is not None
                    second_generation_id = catalog.current_generation_id
                    second_generation = session.get(IndexGeneration, second_generation_id)
                    assert second_generation is not None
                    assert second_generation.parent_id == first_generation_id
                    assert (
                        session.scalar(
                            select(IndexMember).where(
                                IndexMember.generation_id == second_generation_id,
                                IndexMember.revision_id == second_id,
                            )
                        )
                        is not None
                    )
                    assert (
                        session.scalar(
                            select(IndexMember).where(
                                IndexMember.generation_id == second_generation_id,
                                IndexMember.revision_id == first_id,
                            )
                        )
                        is None
                    )

                # Пустое извлечение сохраняется как валидный graph ACK без повтора модели.
                with session_factory.begin() as session:
                    third, created = IngestionService(session).ingest(
                        _document(
                            "Bibliographic record", "A publication record with metadata only."
                        )
                    )
                    assert created
                    third_id = third.id
                with session_factory() as session:
                    qdrant_index = IndexingService(session, qdrant, FakeEmbedder())
                    assert (
                        await qdrant_index.index_revision(third_id, request_id="graph-third-qdrant")
                        == 1
                    )
                third_graph = await graph_index.index_revision(third_id, request_id="graph-third")
                assert third_graph.fact_count == 0
                assert (
                    await graph_index.index_revision(third_id, request_id="graph-third-retry")
                    == third_graph
                )
                assert extractor.calls == ["graph-first", "graph-second", "graph-third"]
                third_root = f"{namespace}:work:{first_document_id}:rev:{third_id}"
                assert await graph.one_hop(third_root) == []
                expected_third = {
                    "qdrant": ("qdrant-test-v1", spec.projection_version),
                    "domain_graph": (third_graph.indexer_version, third_graph.projection_version),
                }
                with session_factory.begin() as session:
                    assert not IngestionService(session).acknowledge(
                        third_id,
                        backend="qdrant",
                        indexer_version=expected_third["qdrant"][0],
                        projection_version=expected_third["qdrant"][1],
                        expected_versions=expected_third,
                    )
                with session_factory.begin() as session:
                    assert IngestionService(session).acknowledge(
                        third_id,
                        backend="domain_graph",
                        indexer_version=expected_third["domain_graph"][0],
                        projection_version=expected_third["domain_graph"][1],
                        expected_versions=expected_third,
                    )
                with session_factory() as session:
                    catalog = session.get(IndexCatalog, 1)
                    assert catalog is not None and catalog.current_generation_id is not None
                    third_generation = session.get(IndexGeneration, catalog.current_generation_id)
                    assert third_generation is not None
                    assert (
                        session.scalar(
                            select(IndexMember).where(
                                IndexMember.generation_id == third_generation.id,
                                IndexMember.revision_id == third_id,
                            )
                        )
                        is not None
                    )

                # Удаление первой ревизии снимает её provenance и сохраняет вторую.
                await graph_index.remove_revision(first_id)
                await qdrant.delete_revision(first_id)
                assert await graph.one_hop(first_root) == []
                assert len(await graph.one_hop(second_root)) == 1

                # После потери Neo4j повтор строит проекцию только по фактам PostgreSQL.
                await graph_index.remove_revision(second_id)
                restored = await graph_index.index_revision(
                    second_id, request_id="graph-second-restored"
                )
                assert restored == second_graph
                assert extractor.calls == ["graph-first", "graph-second", "graph-third"]
                assert len(await graph.one_hop(second_root)) == 1
            finally:
                try:
                    async with driver.session(database="neo4j") as session:
                        result = await session.run(
                            "MATCH (node) WHERE node.namespace = $namespace DETACH DELETE node",
                            namespace=namespace,
                        )
                        await result.consume()
                finally:
                    await qdrant_client.delete(f"/collections/{spec.collection}")
                    await graph.close()
                    engine.dispose()
                    with admin.begin() as connection:
                        connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
                    admin.dispose()

    asyncio.run(exercise())
