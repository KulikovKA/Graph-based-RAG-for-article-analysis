"""Contract checks for the optional LightRAG context boundary."""

import asyncio
import os
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.integrations.lightrag_adapter import (
    LightRAGAdapter,
    LightRAGContext,
    PostgresEvidenceResolver,
    PublicEvidence,
    workspace_from_env,
)
from app.storage.models import (
    DocumentRevision,
    EvidenceChunk,
    IndexGeneration,
    IndexMember,
    SourceDocument,
)


class FakeResolver:
    def __init__(self, evidence: dict[str, PublicEvidence]) -> None:
        self.evidence = evidence
        self.generations: list[UUID] = []

    def resolve(self, keys: set[str], *, generation_id: UUID) -> dict[str, PublicEvidence]:
        self.generations.append(generation_id)
        return {key: self.evidence[key] for key in keys if key in self.evidence}


class FakeLightRAG:
    def __init__(self, references: list[dict[str, str]] | None = None) -> None:
        self.references = references or []
        self.inserted: list[tuple[dict[str, object], str]] = []

    async def ainsert_custom_kg(
        self, knowledge_graph: dict[str, object], *, full_doc_id: str
    ) -> None:
        self.inserted.append((knowledge_graph, full_doc_id))

    async def query_context(self, query: str, *, limit: int) -> dict[str, object]:
        assert query and 1 <= limit <= 50
        return {"status": "success", "data": {"references": self.references}}


def evidence(*, chunk_id: UUID, external_id: str) -> PublicEvidence:
    return PublicEvidence(
        evidence_id=chunk_id,
        chunk_id=chunk_id,
        document_id=uuid4(),
        revision_id=uuid4(),
        text=f"authoritative text for {external_id}",
        source="openalex",
        external_id=external_id,
        title=external_id,
        source_url=f"https://openalex.org/{external_id}",
    )


def test_context_query_uses_only_resolved_postgres_evidence() -> None:
    async def exercise() -> None:
        first, second = uuid4(), uuid4()
        key_a, key_b, stale = f"evidence-{first.hex}", f"evidence-{second.hex}", "chunk-7"
        a = evidence(chunk_id=first, external_id="W1")
        b = evidence(chunk_id=second, external_id="W2")
        runtime = FakeLightRAG([{"file_path": key_a}, {"file_path": stale}, {"file_path": key_b}])
        resolver = FakeResolver({key_a: a, key_b: b})
        generation = uuid4()
        adapter = LightRAGAdapter(runtime, resolver)

        result = await adapter.query("query", generation_id=generation)

        assert result.status == "success"
        assert [record.evidence_id for record in result.evidence] == [first, second]
        assert [record.text for record in result.evidence] == [a.text, b.text]
        assert resolver.generations == [generation]

    asyncio.run(exercise())


def test_adapter_is_optional_and_query_failures_are_isolated() -> None:
    async def exercise() -> None:
        disabled = LightRAGAdapter(None, FakeResolver({}), enabled=True)
        assert await disabled.query("q", generation_id=uuid4()) == LightRAGContext("disabled")

        class BrokenRuntime(FakeLightRAG):
            async def query_context(self, query: str, *, limit: int) -> dict[str, object]:
                raise RuntimeError("sensitive backend details")

        failed = LightRAGAdapter(BrokenRuntime(), FakeResolver({}))
        assert await failed.query("q", generation_id=uuid4()) == LightRAGContext("unavailable")

        class SlowRuntime(FakeLightRAG):
            async def query_context(self, query: str, *, limit: int) -> dict[str, object]:
                await asyncio.sleep(1)
                return {"status": "success", "data": {"references": []}}

        timed_out = LightRAGAdapter(SlowRuntime(), FakeResolver({}), timeout_seconds=0.01)
        assert await timed_out.query("q", generation_id=uuid4()) == LightRAGContext("timeout")

    asyncio.run(exercise())


def test_workspace_rejects_global_donor_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NEO4J_WORKSPACE", raising=False)
    monkeypatch.delenv("QDRANT_WORKSPACE", raising=False)
    monkeypatch.setenv("LIGHTRAG_WORKSPACE", "product_context_v1")
    assert workspace_from_env() == "product_context_v1"
    monkeypatch.setenv("QDRANT_WORKSPACE", "shared")
    with pytest.raises(ValueError, match="overrides"):
        workspace_from_env()


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is required")
def test_postgres_mapping_is_revision_and_generation_scoped() -> None:
    database_url = os.environ["TEST_DATABASE_URL"]
    admin = create_engine(database_url)
    schema = f"lightrag_test_{uuid4().hex}"
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped_url = database_url + ("&" if "?" in database_url else "?")
    scoped_url += f"options=-csearch_path%3D{schema}"
    engine = create_engine(scoped_url)
    factory = sessionmaker(engine, expire_on_commit=False, class_=Session)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", scoped_url.replace("%", "%%"))
    try:
        command.upgrade(config, "head")
        with factory.begin() as session:
            doc_a = SourceDocument(
                source="epo_ops",
                external_id="EP1234567A1",
                canonical_url="https://patents.example/EP1234567A1",
                kind="article",
                title="A",
            )
            doc_b = SourceDocument(
                source="openalex",
                external_id="W-B",
                canonical_url="https://openalex.org/W-B",
                kind="article",
                title="B",
            )
            session.add_all([doc_a, doc_b])
            session.flush()
            old_revision = DocumentRevision(
                document_id=doc_a.id,
                content_hash="a" * 64,
                normalized_json={},
                ingest_state="indexed",
            )
            new_revision = DocumentRevision(
                document_id=doc_a.id,
                content_hash="b" * 64,
                normalized_json={},
                ingest_state="indexed",
            )
            same_text_revision = DocumentRevision(
                document_id=doc_b.id,
                content_hash="c" * 64,
                normalized_json={},
                ingest_state="indexed",
            )
            session.add_all([old_revision, new_revision, same_text_revision])
            session.flush()
            old_chunk = EvidenceChunk(
                revision_id=old_revision.id,
                section="abstract",
                ordinal=0,
                text="same text",
                section_start=0,
                section_end=9,
                hash="d" * 64,
                language="en",
            )
            new_chunk = EvidenceChunk(
                revision_id=new_revision.id,
                section="abstract",
                ordinal=0,
                text="same text",
                section_start=0,
                section_end=9,
                hash="e" * 64,
                language="en",
            )
            other_chunk = EvidenceChunk(
                revision_id=same_text_revision.id,
                section="abstract",
                ordinal=0,
                text="same text",
                section_start=0,
                section_end=9,
                hash="f" * 64,
                language="en",
            )
            session.add_all([old_chunk, new_chunk, other_chunk])
            session.flush()
            doc_a.active_revision_id = new_revision.id
            doc_b.active_revision_id = same_text_revision.id
            current_generation = IndexGeneration(config_versions_json={})
            old_generation = IndexGeneration(config_versions_json={})
            session.add_all([current_generation, old_generation])
            session.flush()
            session.add_all(
                [
                    IndexMember(
                        generation_id=old_generation.id,
                        document_id=doc_a.id,
                        revision_id=old_revision.id,
                    ),
                    IndexMember(
                        generation_id=current_generation.id,
                        document_id=doc_a.id,
                        revision_id=new_revision.id,
                    ),
                    IndexMember(
                        generation_id=current_generation.id,
                        document_id=doc_b.id,
                        revision_id=same_text_revision.id,
                    ),
                ]
            )
            session.flush()
            ids = {
                "old": old_chunk.id,
                "new": new_chunk.id,
                "other": other_chunk.id,
                "generation": current_generation.id,
                "revision": new_revision.id,
            }

        with factory() as session:
            resolver = PostgresEvidenceResolver(session)
            keys = {
                f"evidence-{ids['old'].hex}",
                f"evidence-{ids['new'].hex}",
                f"evidence-{ids['other'].hex}",
            }
            resolved = resolver.resolve(keys, generation_id=ids["generation"])
            assert set(resolved) == {f"evidence-{ids['new'].hex}", f"evidence-{ids['other'].hex}"}
            assert resolved[f"evidence-{ids['new'].hex}"].external_id == "EP1234567A1"
            assert resolved[f"evidence-{ids['other'].hex}"].external_id == "W-B"

            runtime = FakeLightRAG()
            adapter = LightRAGAdapter(runtime, resolver)
            assert (
                asyncio.run(
                    adapter.index_revision(
                        ids["revision"],
                        generation_id=ids["generation"],
                        session=session,
                    )
                )
                == 1
            )
            assert "[reference:evidence-" in str(runtime.inserted[0][0])
            runtime.references = [{"file_path": f"evidence-{ids['new'].hex}"}]
            context = asyncio.run(adapter.query("matching query", generation_id=ids["generation"]))
            assert context.status == "success"
            assert [record.chunk_id for record in context.evidence] == [ids["new"]]
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
