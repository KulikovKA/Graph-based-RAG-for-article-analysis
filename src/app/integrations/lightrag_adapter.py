"""Optional, provenance-safe context adapter for the pinned LightRAG runtime.

LightRAG identifiers are deliberately treated as untrusted lookup hints. The
authoritative text and IDs always come from PostgreSQL after checking the
requested index generation.
"""

from __future__ import annotations

import asyncio
import os
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.storage.models import (
    DocumentRevision,
    EvidenceChunk,
    IndexMember,
    SourceDocument,
)

_KEY_RE = re.compile(r"^evidence-([0-9a-f]{32})$")


@dataclass(frozen=True)
class PublicEvidence:
    evidence_id: UUID
    chunk_id: UUID
    document_id: UUID
    revision_id: UUID
    text: str
    source: str
    external_id: str
    title: str
    source_url: str


@dataclass(frozen=True)
class LightRAGContext:
    status: str
    evidence: tuple[PublicEvidence, ...] = ()


class LightRAGRuntime(Protocol):
    async def ainsert_custom_kg(
        self, knowledge_graph: dict[str, Any], *, full_doc_id: str
    ) -> None: ...

    async def query_context(self, query: str, *, limit: int) -> dict[str, Any]: ...


class EvidenceResolver(Protocol):
    def resolve(self, keys: set[str], *, generation_id: UUID) -> dict[str, PublicEvidence]: ...


class PinnedLightRAGRuntime:
    """Thin wrapper around the pinned public LightRAG query/insert APIs."""

    def __init__(self, rag: Any) -> None:
        self.rag = rag

    async def ainsert_custom_kg(self, knowledge_graph: dict[str, Any], *, full_doc_id: str) -> None:
        await self.rag.ainsert_custom_kg(knowledge_graph, full_doc_id=full_doc_id)

    async def query_context(self, query: str, *, limit: int) -> dict[str, Any]:
        from lightrag import QueryParam  # type: ignore[import-not-found]

        keywords = re.findall(r"[\w-]{3,}", query, flags=re.UNICODE)[:8]
        param = QueryParam(
            mode="mix",
            only_need_context=True,
            enable_rerank=False,
            top_k=limit,
            chunk_top_k=limit,
            hl_keywords=keywords,
            ll_keywords=keywords,
        )
        return cast(dict[str, Any], await self.rag.aquery_data(query, param=param))


def create_pinned_runtime(
    *,
    working_dir: str,
    embedding_model_id: str,
    embedding_dimensions: int,
    embed: Callable[[list[str]], Awaitable[list[list[float]]]],
    workspace: str | None = None,
) -> PinnedLightRAGRuntime:
    """Build the optional runtime with its own namespace and app-provided embeddings."""
    if not working_dir or not embedding_model_id or embedding_dimensions < 1:
        raise ValueError("invalid LightRAG runtime configuration")
    from lightrag import LightRAG
    from lightrag.utils import EmbeddingFunc  # type: ignore[import-not-found]

    if os.getenv("NEO4J_WORKSPACE") or os.getenv("QDRANT_WORKSPACE"):
        raise ValueError("LightRAG global workspace overrides are not allowed")
    selected_workspace = (
        workspace or os.getenv("LIGHTRAG_WORKSPACE") or "article_analysis_public_v1"
    )
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", selected_workspace):
        raise ValueError("invalid LightRAG workspace")

    async def no_generation(*_args: Any, **_kwargs: Any) -> str:
        raise RuntimeError("LightRAG generation is disabled")

    rag = LightRAG(
        working_dir=working_dir,
        workspace=selected_workspace,
        graph_storage="Neo4JStorage",
        vector_storage="QdrantVectorDBStorage",
        llm_model_func=no_generation,
        embedding_func=EmbeddingFunc(
            embedding_dim=embedding_dimensions,
            max_token_size=8192,
            model_name=embedding_model_id,
            func=embed,
        ),
    )
    return PinnedLightRAGRuntime(rag)


class PostgresEvidenceResolver:
    """Resolve opaque LightRAG keys to public evidence in the pinned generation."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def resolve(self, keys: set[str], *, generation_id: UUID) -> dict[str, PublicEvidence]:
        parsed: dict[str, UUID] = {}
        for key in keys:
            match = _KEY_RE.fullmatch(key)
            if match:
                parsed[key] = UUID(hex=match.group(1))
        if not parsed:
            return {}

        rows = self.session.execute(
            select(EvidenceChunk, DocumentRevision, SourceDocument)
            .join(DocumentRevision, DocumentRevision.id == EvidenceChunk.revision_id)
            .join(SourceDocument, SourceDocument.id == DocumentRevision.document_id)
            .join(
                IndexMember,
                (IndexMember.revision_id == DocumentRevision.id)
                & (IndexMember.document_id == DocumentRevision.document_id),
            )
            .where(
                IndexMember.generation_id == generation_id,
                EvidenceChunk.id.in_(set(parsed.values())),
                SourceDocument.source.in_(("epo_ops", "openalex")),
            )
        ).all()
        by_chunk = {chunk.id: (chunk, revision, document) for chunk, revision, document in rows}
        resolved: dict[str, PublicEvidence] = {}
        for key, chunk_id in parsed.items():
            row = by_chunk.get(chunk_id)
            if row is None:
                continue
            chunk, revision, document = row
            resolved[key] = PublicEvidence(
                evidence_id=chunk.id,
                chunk_id=chunk.id,
                document_id=document.id,
                revision_id=revision.id,
                text=chunk.text,
                source=document.source,
                external_id=document.external_id,
                title=document.title,
                source_url=document.canonical_url,
            )
        return resolved


class LightRAGAdapter:
    """Bounded context-only adapter; failures never become product answers."""

    def __init__(
        self,
        runtime: LightRAGRuntime | None,
        resolver: EvidenceResolver,
        *,
        enabled: bool = True,
        timeout_seconds: float = 3.0,
        max_results: int = 10,
    ) -> None:
        if timeout_seconds <= 0 or not 1 <= max_results <= 50:
            raise ValueError("invalid LightRAG bounds")
        self.runtime = runtime
        self.resolver = resolver
        self.enabled = enabled and runtime is not None
        self.timeout_seconds = timeout_seconds
        self.max_results = max_results

    async def index_revision(
        self, revision_id: UUID, *, generation_id: UUID, session: Session
    ) -> int:
        """Project a public revision only after it is a member of the pinned generation."""
        if not self.enabled or self.runtime is None:
            return 0
        members = session.execute(
            select(EvidenceChunk, DocumentRevision, SourceDocument)
            .join(DocumentRevision, DocumentRevision.id == EvidenceChunk.revision_id)
            .join(SourceDocument, SourceDocument.id == DocumentRevision.document_id)
            .join(
                IndexMember,
                (IndexMember.revision_id == DocumentRevision.id)
                & (IndexMember.document_id == DocumentRevision.document_id),
            )
            .where(
                IndexMember.generation_id == generation_id,
                DocumentRevision.id == revision_id,
                SourceDocument.source.in_(("epo_ops", "openalex")),
            )
            .order_by(EvidenceChunk.section, EvidenceChunk.ordinal)
        ).all()
        count = 0
        for chunk, revision, _document in members:
            key = f"evidence-{chunk.id.hex}"
            # The suffix prevents donor content-hash collisions for identical text
            # belonging to different evidence chunks. It is never returned as evidence.
            kg = {
                "chunks": [
                    {
                        "content": f"{chunk.text}\n\n[reference:{key}]",
                        "source_id": key,
                        "chunk_order_index": chunk.ordinal,
                        "file_path": key,
                    }
                ],
                "entities": [],
                "relationships": [],
            }
            await asyncio.wait_for(
                self.runtime.ainsert_custom_kg(kg, full_doc_id=f"revision-{revision.id.hex}"),
                timeout=self.timeout_seconds,
            )
            count += 1
        return count

    async def query(self, query: str, *, generation_id: UUID) -> LightRAGContext:
        if not self.enabled or self.runtime is None:
            return LightRAGContext(status="disabled")
        if not query.strip():
            return LightRAGContext(status="empty_query")
        try:
            result = await asyncio.wait_for(
                self.runtime.query_context(query[:4000], limit=self.max_results),
                timeout=self.timeout_seconds,
            )
        except TimeoutError:
            return LightRAGContext(status="timeout")
        except Exception:
            # Do not propagate provider exception bodies into API, logs, or answer text.
            return LightRAGContext(status="unavailable")

        if not isinstance(result, dict) or result.get("status") != "success":
            return LightRAGContext(status="unavailable")
        data = result.get("data")
        if not isinstance(data, dict):
            return LightRAGContext(status="empty")
        references = data.get("references", [])
        keys = {
            item["file_path"]
            for item in references
            if isinstance(item, dict) and isinstance(item.get("file_path"), str)
        }
        resolved = self.resolver.resolve(keys, generation_id=generation_id)
        # Stable order follows LightRAG rank, while only verified PostgreSQL rows survive.
        evidence: list[PublicEvidence] = []
        seen: set[UUID] = set()
        for item in references:
            key = item.get("file_path") if isinstance(item, dict) else None
            record = resolved.get(key) if isinstance(key, str) else None
            if record is not None and record.evidence_id not in seen:
                evidence.append(record)
                seen.add(record.evidence_id)
            if len(evidence) == self.max_results:
                break
        return LightRAGContext(status="success" if evidence else "empty", evidence=tuple(evidence))


def workspace_from_env() -> str:
    """Require an explicit adapter namespace and reject donor global overrides."""
    if os.getenv("NEO4J_WORKSPACE") or os.getenv("QDRANT_WORKSPACE"):
        raise ValueError("LightRAG global workspace overrides are not allowed")
    workspace = os.getenv("LIGHTRAG_WORKSPACE", "article_analysis_public_v1").strip()
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", workspace):
        raise ValueError("invalid LightRAG workspace")
    return workspace
