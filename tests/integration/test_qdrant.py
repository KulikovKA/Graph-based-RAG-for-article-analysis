"""Real Qdrant and PostgreSQL projection tests (isolated collection and schema)."""

import asyncio
import os
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.domain.documents import DocumentSection, NormalizedDocument
from app.integrations.inference_http import OllamaProvider
from app.integrations.qdrant import EmbeddingSpec, QdrantIndex
from app.services.indexing import IndexingService
from app.services.ingestion import IngestionService
from app.storage.models import IndexCatalog, IndexGeneration
from app.workers.inference import GenerationGate

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL") or not os.getenv("TEST_QDRANT_URL"),
    reason="TEST_DATABASE_URL and TEST_QDRANT_URL are required",
)


class FakeEmbedder:
    def __init__(self, dimension: int = 2) -> None:
        self.dimension = dimension

    async def embed(self, *, model_id: str, request_id: str,
                    texts: list[str]) -> list[list[float]]:
        return [[float(len(value)), 1.0] for value in texts] if self.dimension == 2 else [
            [1.0] for _ in texts
        ]


def _document(abstract: str) -> NormalizedDocument:
    return NormalizedDocument(
        source="openalex", external_id="W999999901", canonical_url="https://openalex.org/W999999901",
        kind="article", title="Indexed article", publication_date=None, source_updated_at=None,
        sections=(DocumentSection("abstract", abstract, "en"),), metadata={},
    )


def test_projection_reindex_dimensions_and_generation_membership() -> None:
    async def exercise() -> None:
        db_url = os.environ["TEST_DATABASE_URL"]
        admin = create_engine(db_url)
        schema = f"qdrant_test_{uuid4().hex}"
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        scoped_url = db_url + ("&" if "?" in db_url else "?") + f"options=-csearch_path%3D{schema}"
        engine = create_engine(scoped_url)
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", scoped_url.replace("%", "%%"))
        spec = EmbeddingSpec(f"idx_test_{uuid4().hex}", "fixture-embedding", "v1", 2)
        async with httpx.AsyncClient(base_url=os.environ["TEST_QDRANT_URL"], timeout=20) as client:
            index = QdrantIndex(client, spec)
            try:
                command.upgrade(config, "head")
                with Session(engine) as session:
                    ingestion = IngestionService(session)
                    first, _ = ingestion.ingest(_document("First abstract about turbines."))
                    session.flush()
                    service = IndexingService(session, index, FakeEmbedder())
                    assert await service.index_revision(first.id, request_id="first") == 1
                    assert await service.index_revision(first.id, request_id="again") == 1
                    assert await index.count() == 1
                    assert await index.count(revision_id=first.id) == 1
                    expected = {"qdrant": ("idx-v1", spec.projection_version),
                                "domain_graph": ("idx-v1", "projection-v1")}
                    assert not ingestion.acknowledge(first.id, backend="qdrant",
                        indexer_version="idx-v1", projection_version=spec.projection_version,
                        expected_versions=expected)
                    assert ingestion.acknowledge(first.id, backend="domain_graph",
                        indexer_version="idx-v1", projection_version="projection-v1",
                        expected_versions=expected)
                    catalog = session.get(IndexCatalog, 1)
                    assert catalog is not None
                    generation = catalog.current_generation_id
                    assert generation is not None
                    generation_row = session.get(IndexGeneration, generation)
                    assert generation_row is not None
                    assert generation_row.config_versions_json["qdrant"][
                        "projection_version"] == spec.projection_version
                    assert len(await service.search([1.0, 1.0], generation_id=generation,
                                                    limit=10, source="openalex")) == 1
                    assert await service.search([1.0, 1.0], generation_id=generation,
                                                limit=10, source="epo_ops") == []
                    assert await service.search([1.0, 1.0], generation_id=generation,
                                                limit=10, source_id="W000") == []
                    assert len(await service.search([1.0, 1.0], generation_id=generation,
                                                    limit=10, section="abstract",
                                                    language="en")) == 1
                    assert await index.query([1.0, 1.0], limit=10, document_ids=[]) == []

                    changed, _ = ingestion.ingest(_document("Changed abstract about turbines."))
                    assert await service.index_revision(changed.id, request_id="staged") == 1
                    assert await index.count() == 2
                    hits = await service.search([1.0, 1.0], generation_id=generation, limit=10)
                    assert [hit.revision_id for hit in hits] == [first.id]
                    bad_service = IndexingService(session, index, FakeEmbedder(dimension=1))
                    with pytest.raises(ValueError, match="dimension mismatch"):
                        await bad_service.index_revision(changed.id, request_id="wrong-size")
                    assert await index.count() == 2
                    assert not ingestion.acknowledge(changed.id, backend="qdrant",
                        indexer_version="idx-v1", projection_version=spec.projection_version,
                        expected_versions=expected)
                    assert ingestion.acknowledge(changed.id, backend="domain_graph",
                        indexer_version="idx-v1", projection_version="projection-v1",
                        expected_versions=expected)
                    catalog = session.get(IndexCatalog, 1)
                    assert catalog is not None
                    new_generation = catalog.current_generation_id
                    assert new_generation is not None
                    new_hits = await service.search([1.0, 1.0], generation_id=new_generation,
                                                    limit=10)
                    assert [hit.revision_id for hit in new_hits] == [changed.id]
                    await service.delete_revision(changed.id)
                    await service.delete_revision(changed.id)
                    assert await index.count(revision_id=changed.id) == 0
            finally:
                await client.delete(f"/collections/{spec.collection}")
                engine.dispose()
                with admin.begin() as connection:
                    connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
                admin.dispose()

    asyncio.run(exercise())


@pytest.mark.skipif(not os.getenv("TEST_OLLAMA_URL"), reason="TEST_OLLAMA_URL is required")
def test_pinned_embedding_projects_real_vectors() -> None:
    async def exercise() -> None:
        db_url = os.environ["TEST_DATABASE_URL"]
        admin = create_engine(db_url)
        schema = f"qdrant_real_{uuid4().hex}"
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        scoped_url = db_url + ("&" if "?" in db_url else "?") + f"options=-csearch_path%3D{schema}"
        engine = create_engine(scoped_url)
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", scoped_url.replace("%", "%%"))
        spec = EmbeddingSpec.from_config(
            f"idx_real_{uuid4().hex}", Path("config/models.yaml")
        )
        changed_spec = EmbeddingSpec(spec.namespace, spec.model_id,
                                     "replacement-digest", spec.dimension)
        assert changed_spec.collection != spec.collection
        assert changed_spec.projection_version != spec.projection_version
        async with (httpx.AsyncClient(base_url=os.environ["TEST_QDRANT_URL"], timeout=30)
                    as qdrant_client,
                    httpx.AsyncClient(base_url=os.environ["TEST_OLLAMA_URL"], timeout=90)
                    as ollama_client):
            index = QdrantIndex(qdrant_client, spec)
            provider = OllamaProvider(ollama_client, gate=GenerationGate(),
                                      model_revisions={}, supported_efforts={})
            try:
                tags = (await ollama_client.get("/api/tags")).json()["models"]
                actual = next(item for item in tags if item["name"] == spec.model_id)
                assert actual["digest"] == spec.model_version
                command.upgrade(config, "head")
                with Session(engine) as session:
                    ingestion = IngestionService(session)
                    first, _ = ingestion.ingest(_document(
                        "A heat pump recovers industrial waste heat for district heating."
                    ))
                    session.flush()
                    service = IndexingService(session, index, provider)
                    assert await service.index_revision(first.id, request_id="real-first") == 1
                    assert await service.index_revision(first.id, request_id="real-repeat") == 1
                    assert await index.count() == 1
                    query = (await provider.embed(model_id=spec.model_id, request_id="query",
                                                  texts=["district heating heat pump"]))[0]
                    assert len(query) == spec.dimension
                    with pytest.raises(ValueError, match="dimension mismatch"):
                        await index.query(query[:-1], limit=1)
                    expected = {"qdrant": ("idx-v1", spec.projection_version),
                                "domain_graph": ("idx-v1", "projection-v1")}
                    assert not ingestion.acknowledge(first.id, backend="qdrant",
                        indexer_version="idx-v1", projection_version=spec.projection_version,
                        expected_versions=expected)
                    assert ingestion.acknowledge(first.id, backend="domain_graph",
                        indexer_version="idx-v1", projection_version="projection-v1",
                        expected_versions=expected)
                    catalog = session.get(IndexCatalog, 1)
                    assert catalog is not None
                    generation = catalog.current_generation_id
                    assert generation is not None
                    generation_row = session.get(IndexGeneration, generation)
                    assert generation_row is not None
                    assert generation_row.config_versions_json["qdrant"][
                        "projection_version"] == spec.projection_version
                    hits = await service.search(query, generation_id=generation, limit=10,
                                                source="openalex", section="abstract")
                    assert len(hits) == 1 and hits[0].revision_id == first.id
                    point = (await qdrant_client.post(
                        f"/collections/{spec.collection}/points",
                        json={"ids": [str(hits[0].chunk_id)], "with_payload": True},
                    )).json()["result"][0]
                    assert point["payload"] == {
                        "document_id": str(hits[0].document_id),
                        "revision_id": str(first.id),
                        "chunk_id": str(hits[0].chunk_id),
                        "source": "openalex", "source_id": "W999999901",
                        "section": "abstract", "language": "en",
                    }
                    assert await service.search(query, generation_id=generation, limit=10,
                                                source="epo_ops") == []
                    alternate = QdrantIndex(qdrant_client, changed_spec)
                    await alternate.ensure_collection()
                    assert await alternate.count() == 0
                    with pytest.raises(ValueError, match="projection version mismatch"):
                        await IndexingService(session, alternate, provider).search(
                            query, generation_id=generation, limit=10
                        )
            finally:
                await qdrant_client.delete(f"/collections/{spec.collection}")
                await qdrant_client.delete(f"/collections/{changed_spec.collection}")
                engine.dispose()
                with admin.begin() as connection:
                    connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
                admin.dispose()

    asyncio.run(exercise())
