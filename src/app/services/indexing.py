"""Projection of immutable PostgreSQL chunks into Qdrant and generation-safe lookup."""

from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.qdrant import QdrantIndex, VectorHit, VectorPoint
from app.storage.models import (
    DocumentRevision,
    EvidenceChunk,
    IndexGeneration,
    IndexMember,
    SourceDocument,
)


class Embedder(Protocol):
    async def embed(self, *, model_id: str, request_id: str,
                    texts: list[str]) -> list[list[float]]: ...


class IndexingService:
    def __init__(self, session: Session, index: QdrantIndex, embedder: Embedder) -> None:
        self.session = session
        self.index = index
        self.embedder = embedder

    async def index_revision(self, revision_id: UUID, *, request_id: str) -> int:
        """Upsert all chunks; caller may ACK only after this method returns successfully."""
        row = self.session.execute(
            select(DocumentRevision, SourceDocument)
            .join(SourceDocument, SourceDocument.id == DocumentRevision.document_id)
            .where(DocumentRevision.id == revision_id)
        ).one_or_none()
        if row is None:
            raise LookupError("revision not found")
        revision, document = row
        chunks = list(self.session.scalars(
            select(EvidenceChunk).where(EvidenceChunk.revision_id == revision_id)
            .order_by(EvidenceChunk.section, EvidenceChunk.ordinal)
        ))
        await self.index.ensure_collection()
        for start in range(0, len(chunks), 64):
            batch = chunks[start:start + 64]
            vectors = await self.embedder.embed(
                model_id=self.index.spec.model_id,
                request_id=request_id,
                texts=[item.text for item in batch],
            )
            if len(vectors) != len(batch):
                raise ValueError("embedding count mismatch")
            await self.index.upsert([
                VectorPoint(
                    chunk_id=chunk.id, document_id=revision.document_id,
                    revision_id=revision.id, source=document.source,
                    source_id=document.external_id,
                    section=chunk.section, language=chunk.language, vector=vector,
                )
                for chunk, vector in zip(batch, vectors, strict=True)
            ])
        # A successful ACK must mean that the complete projection is present.
        if await self.index.count(revision_id=revision_id) != len(chunks):
            raise RuntimeError("Qdrant revision projection is incomplete")
        return len(chunks)

    async def delete_revision(self, revision_id: UUID) -> None:
        await self.index.delete_revision(revision_id)

    async def search(
        self, vector: list[float], *, generation_id: UUID, limit: int,
        source: str | None = None, source_id: str | None = None,
        section: str | None = None, language: str | None = None,
    ) -> list[VectorHit]:
        """Check Qdrant candidates against the pinned PostgreSQL generation."""
        if not 1 <= limit <= 100:
            raise ValueError("invalid search limit")
        generation = self.session.get(IndexGeneration, generation_id)
        if generation is None:
            raise LookupError("index generation not found")
        qdrant_version = generation.config_versions_json.get("qdrant", {})
        if qdrant_version.get("projection_version") != self.index.spec.projection_version:
            raise ValueError("embedding projection version mismatch")
        results: list[VectorHit] = []
        offset = 0
        while len(results) < limit:
            candidates = await self.index.query(
                vector, limit=100, offset=offset, source=source,
                source_id=source_id, section=section, language=language,
            )
            if not candidates:
                break
            offset += len(candidates)
            ids = [hit.chunk_id for hit in candidates]
            valid = set(self.session.execute(
                select(EvidenceChunk.id, EvidenceChunk.revision_id, DocumentRevision.document_id)
                .join(DocumentRevision, DocumentRevision.id == EvidenceChunk.revision_id)
                .join(IndexMember,
                      (IndexMember.revision_id == DocumentRevision.id)
                      & (IndexMember.document_id == DocumentRevision.document_id))
                .join(SourceDocument, SourceDocument.id == DocumentRevision.document_id)
                .where(IndexMember.generation_id == generation_id,
                       EvidenceChunk.id.in_(ids),
                       *([SourceDocument.source == source] if source is not None else []),
                       *([SourceDocument.external_id == source_id]
                         if source_id is not None else []),
                       *([EvidenceChunk.section == section] if section is not None else []),
                       *([EvidenceChunk.language == language] if language is not None else []))
            ).all())
            results.extend(hit for hit in candidates if (
                hit.chunk_id, hit.revision_id, hit.document_id
            ) in valid)
            if len(candidates) < 100:
                break
        return results[:limit]
