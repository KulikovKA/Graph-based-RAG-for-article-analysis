"""Bounded corpus ingestion through the production document and index services."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shlex
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import httpx
import yaml
from neo4j import AsyncGraphDatabase
from sqlalchemy.exc import SQLAlchemyError

from app.domain.inference import InferenceProtocolError
from app.domain.source import SourceStatus
from app.integrations.epo import EpoOpsClient
from app.integrations.inference_http import OllamaProvider
from app.integrations.neo4j import PROJECTION_VERSION, Neo4jGraph
from app.integrations.openalex import OpenAlexClient
from app.integrations.qdrant import EmbeddingSpec, QdrantIndex
from app.services.graph_index import (
    EXTRACTOR_VERSION,
    GraphExtractionError,
    VOCABULARY_VERSION,
    GraphIndexingService,
    InferenceGraphExtractor,
)
from app.services.indexing import IndexingService
from app.services.ingestion import IngestionService
from app.storage.repositories import make_engine, make_session_factory
from app.workers.inference import GenerationGate
from app.workers.ingest import from_epo, from_openalex


@dataclass
class RunCounts:
    fetched: int = 0
    eligible: int = 0
    skipped: int = 0
    skipped_no_text: int = 0
    skipped_invalid: int = 0
    previewed: int = 0
    normalized: int = 0
    ingested: int = 0
    new_revisions: int = 0
    reused_revisions: int = 0
    indexed: int = 0
    qdrant_indexed: int = 0
    qdrant_points: int = 0
    graph_processed: int = 0
    graph_projected: int = 0
    graph_facts: int = 0
    graph_extraction_seconds: float = 0.0
    graph_extraction_splits: int = 0
    qdrant_acked: int = 0
    neo4j_acked: int = 0
    activated: int = 0
    errors: int = 0
    failed: int = 0
    fatal_errors: int = 0
    retries: int = 0
    wall_seconds: float = 0.0


class Checkpoint:
    """Atomically persisted cursor and run identity; reject unsafe resume drift."""

    def __init__(self, path: Path, identity: dict[str, Any], *, persist: bool = True) -> None:
        self.path = path
        self.identity = identity
        self.persist = persist
        self.state: dict[str, Any] = {}

    def load(self, *, resume: bool, run_id: str | None) -> None:
        if not resume:
            if self.path.exists():
                raise ValueError(f"checkpoint already exists; use --resume: {self.path}")
            self.state = {
                "schema_version": 1,
                "identity": self.identity,
                "run_id": run_id,
                "cursor": "*",
                "completed": [],
                "counts": asdict(RunCounts()),
                "updated_at": _now(),
            }
            self.save()
            return
        try:
            state = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("checkpoint is missing or invalid") from exc
        if not isinstance(state, dict) or state.get("schema_version") != 1:
            raise ValueError("checkpoint is missing or invalid")
        if state.get("identity") != self.identity:
            raise ValueError("checkpoint configuration/version mismatch")
        if run_id is not None and state.get("run_id") != run_id:
            raise ValueError("checkpoint run_id mismatch")
        self.state = state

    def save(self) -> None:
        if not self.persist:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.state["updated_at"] = _now()
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(self.state, indent=2, ensure_ascii=False), encoding="utf-8")
        temporary.replace(self.path)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _run_identity(
    query: str,
    filters: str | None,
    config_path: Path,
    *,
    source: str,
    max_documents: int,
    batch_size: int,
    dry_run: bool,
) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    embedding = config["embedding"]
    graph = config["generation"]["graph_extractor"]
    identity = {
        "source": source,
        "query": query,
        "filter": filters,
        "max_documents": max_documents,
        "batch_size": batch_size,
        "embedding_model": embedding["model_id"],
        "embedding_digest": embedding["digest"],
        "dimension": embedding["dimension"],
        "graph_model": graph["model_id"],
        "graph_digest": graph["digest"],
        "extractor_version": graph["extractor_version"],
        "graph_output_tokens": graph["max_output_tokens"],
        "graph_context_window": graph["context_window"],
        "graph_timeout_seconds": graph["timeout_seconds"],
        "graph_temperature": graph["temperature"],
        "graph_reasoning_efforts": graph["reasoning_efforts"],
        "graph_projection_version": PROJECTION_VERSION,
        "graph_indexer_version": EXTRACTOR_VERSION,
        "graph_vocabulary_version": VOCABULARY_VERSION,
        "config_identity": hashlib.sha256(config_path.read_bytes()).hexdigest(),
    }
    identity["sha256"] = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return identity


class _NonThinkingClient:
    """Apply the LLM-003 production profile selected for the Graph role."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    def stream(self, method: str, url: str, **kwargs: Any) -> Any:
        body = kwargs.get("json")
        if isinstance(body, dict) and url.endswith("/api/chat"):
            kwargs["json"] = {**body, "think": False}
        return self._client.stream(method, url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        try:
            response = await self._client.post(url, **kwargs)
        except httpx.HTTPError as exc:
            if url.endswith("/api/embed"):
                print(
                    json.dumps({"stage": "embedding_transport_error", "error": type(exc).__name__}),
                    flush=True,
                )
            raise
        if url.endswith("/api/embed") and response.is_error:
            print(
                json.dumps({"stage": "embedding_http_error", "status_code": response.status_code}),
                flush=True,
            )
        return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)


class _ProgressEmbedder:
    def __init__(self, embedder: Any, emit: Callable[[dict[str, Any]], None], work_id: str) -> None:
        self.embedder = embedder
        self.emit = emit
        self.work_id = work_id

    async def embed(self, *, model_id: str, request_id: str, texts: list[str]) -> list[list[float]]:
        try:
            vectors = await self.embedder.embed(
                model_id=model_id, request_id=request_id, texts=texts
            )
        except Exception as exc:
            self.emit(
                {
                    "stage": "embedding_failed",
                    "work_id": self.work_id,
                    "error": type(exc).__name__,
                    "detail": str(exc) if type(exc).__module__ == "app.domain.inference" else None,
                }
            )
            raise
        self.emit(
            {
                "stage": "embedding_batch_complete",
                "work_id": self.work_id,
                "texts": len(texts),
                "vectors": len(vectors),
            }
        )
        return cast(list[list[float]], vectors)


class CorpusPilot:
    """Small resumable runner with all document writes delegated to production services."""

    def __init__(
        self,
        *,
        client: Any,
        source: str = "openalex",
        session_factory: Any,
        qdrant: QdrantIndex,
        embedder: Any,
        graph_index: GraphIndexingService,
        run_id: str,
        emit: Callable[[dict[str, Any]], None] = lambda event: print(
            json.dumps(event, ensure_ascii=False), flush=True
        ),
    ) -> None:
        self.client = client
        self.source = source
        self.session_factory = session_factory
        self.qdrant = qdrant
        self.embedder = embedder
        self.graph_index = graph_index
        self.run_id = run_id
        self.emit = emit

    def _event(self, stage: str, **values: Any) -> None:
        self.emit({"run_id": self.run_id, "source": self.source, "stage": stage, **values})

    async def run(
        self,
        *,
        query: str,
        max_documents: int,
        dry_run: bool,
        checkpoint: Checkpoint | None = None,
        batch_size: int = 25,
        filters: str | None = None,
        only_work_id: str | None = None,
    ) -> RunCounts:
        run_started = time.monotonic()
        counts = RunCounts(**(checkpoint.state.get("counts", {}) if checkpoint else {}))
        errors_at_start = counts.errors
        initial_cursor = "*" if self.source == "openalex" else "0"
        cursor: str | None = (
            checkpoint.state.get("cursor", initial_cursor) if checkpoint else initial_cursor
        )
        seen: set[str] = set()
        completed = set(checkpoint.state.get("completed", [])) if checkpoint else set()
        halted = False
        pending_failure_ids = {
            item.get("work_id")
            for item in (checkpoint.state.get("failures", []) if checkpoint else [])
            if isinstance(item, dict) and item.get("work_id") not in completed
        }
        completed_work = (counts.eligible or (counts.ingested + counts.previewed)) - len(
            pending_failure_ids
        )
        while cursor is not None and completed_work < max_documents:
            page_cursor = cursor
            if self.source == "openalex":
                page = await self.client.search(
                    query, per_page=min(100, batch_size), cursor=page_cursor, filters=filters
                )
                candidates = page.works
                next_cursor = page.next_cursor
            else:
                page = await self.client.search(
                    query,
                    limit=min(100, batch_size),
                    offset=int(page_cursor),
                    filters=filters,
                )
                candidates = page.documents
                next_cursor = str(page.next_offset) if page.next_offset is not None else None
            if page.status == SourceStatus.NOT_CONFIGURED:
                self._event("source_skipped", reason="credentials_not_configured")
                break
            if page.status == SourceStatus.EMPTY:
                break
            if page.status != SourceStatus.OK:
                counts.errors += 1
                counts.failed += 1
                counts.fatal_errors += 1
                self._event("search_failed", status=page.status.value, error=page.error_code)
                break
            target_work_done = False
            for candidate in candidates:
                if completed_work >= max_documents:
                    break
                if only_work_id is not None and candidate.external_id != only_work_id:
                    continue
                if candidate.external_id in seen:
                    continue
                seen.add(candidate.external_id)
                if candidate.external_id in completed:
                    target_work_done = candidate.external_id == only_work_id
                    if target_work_done:
                        break
                    continue
                if self.source == "openalex":
                    fetched = await self.client.fetch(candidate.external_id)
                    source_documents = fetched.works
                else:
                    fetched = await self.client.fetch(candidate.external_id, include_fulltext=True)
                    source_documents = fetched.documents
                if fetched.status != SourceStatus.OK or not source_documents:
                    counts.errors += 1
                    counts.failed += 1
                    counts.fatal_errors += 1
                    self._event(
                        "fetch_failed", work_id=candidate.external_id, error=fetched.error_code
                    )
                    halted = True
                    break
                source_document = source_documents[0]
                counts.fetched += 1
                title = source_document.title
                sections = (
                    [source_document.abstract or ""]
                    if self.source == "openalex"
                    else [
                        source_document.abstract or "",
                        source_document.claims or "",
                        source_document.description or "",
                    ]
                )
                usable_text = any(section.strip() for section in sections)
                if (
                    not title
                    or not title.strip()
                    or not usable_text
                    or sum(len(section.strip()) for section in sections) < 80
                ):
                    counts.skipped += 1
                    counts.skipped_no_text += 1
                    completed.add(source_document.external_id)
                    self._event(
                        "skipped",
                        work_id=source_document.external_id,
                        reason="insufficient_abstract",
                        counts=asdict(counts),
                    )
                    if checkpoint:
                        checkpoint.state.update(
                            cursor=page_cursor, completed=sorted(completed), counts=asdict(counts)
                        )
                        checkpoint.save()
                    if only_work_id is not None:
                        target_work_done = True
                        break
                    continue
                counts.eligible += 1
                completed_work += 1
                normalized = (
                    from_openalex(source_document)
                    if self.source == "openalex"
                    else from_epo(source_document)
                )
                counts.normalized += 1
                if dry_run:
                    counts.previewed += 1
                    if checkpoint:
                        checkpoint.state.update(
                            cursor=page_cursor, completed=sorted(completed), counts=asdict(counts)
                        )
                        checkpoint.save()
                    self._event(
                        "would_ingest",
                        work_id=source_document.external_id,
                        title=title,
                        counts=asdict(counts),
                    )
                    if only_work_id is not None:
                        target_work_done = True
                        break
                    continue
                started = time.monotonic()
                failed_at = "postgres_ingestion"
                try:
                    with self.session_factory.begin() as session:
                        revision, created = IngestionService(session).ingest(normalized)
                        revision_id = revision.id
                    failed_at = "qdrant_embedding_index"
                    with self.session_factory() as session:
                        embedder = _ProgressEmbedder(
                            self.embedder,
                            lambda event: self.emit({"run_id": self.run_id, **event}),
                            source_document.external_id,
                        )
                        qdrant_index = IndexingService(session, self.qdrant, embedder)
                        point_count = await qdrant_index.index_revision(
                            revision_id,
                            request_id=f"{self.run_id}:{source_document.external_id}:qdrant",
                        )
                    counts.qdrant_indexed += 1
                    counts.qdrant_points += point_count
                    qdrant_version = ("qdrant-indexer-v1", self.qdrant.spec.projection_version)
                    failed_at = "graph_extraction_neo4j_projection"
                    graph_started = time.monotonic()
                    graph_result = await self.graph_index.index_revision(
                        revision_id,
                        request_id=f"{self.run_id}:{source_document.external_id}:graph",
                    )
                    graph_seconds = time.monotonic() - graph_started
                    counts.graph_processed += 1
                    extraction_seconds = float(getattr(graph_result, "extraction_seconds", 0.0))
                    extraction_splits = int(getattr(graph_result, "extraction_splits", 0))
                    counts.graph_extraction_seconds += extraction_seconds
                    counts.graph_extraction_splits += extraction_splits
                    expected = {
                        "qdrant": qdrant_version,
                        "domain_graph": (
                            graph_result.indexer_version,
                            graph_result.projection_version,
                        ),
                    }
                    with self.session_factory.begin() as session:
                        failed_at = "postgres_ack_generation"
                        ingestion = IngestionService(session)
                        ingestion.acknowledge(
                            revision_id,
                            backend="qdrant",
                            indexer_version=qdrant_version[0],
                            projection_version=qdrant_version[1],
                            expected_versions=expected,
                        )
                        activated = ingestion.acknowledge(
                            revision_id,
                            backend="domain_graph",
                            indexer_version=graph_result.indexer_version,
                            projection_version=graph_result.projection_version,
                            expected_versions=expected,
                        )
                    counts.qdrant_acked += 1
                    counts.neo4j_acked += 1
                    if not activated:
                        raise RuntimeError(
                            "required index acknowledgements did not activate revision"
                        )
                    counts.ingested += 1
                    if created:
                        counts.new_revisions += 1
                    else:
                        counts.reused_revisions += 1
                    counts.indexed += 1
                    counts.activated += 1
                    counts.graph_projected += 1
                    counts.graph_facts += graph_result.fact_count
                    completed.add(source_document.external_id)
                    if checkpoint:
                        checkpoint.state.update(
                            cursor=page_cursor,
                            completed=sorted(completed),
                            counts=asdict(counts),
                        )
                        checkpoint.save()
                    self._event(
                        "document_complete",
                        work_id=source_document.external_id,
                        title=title,
                        revision_id=str(revision_id),
                        new_revision=created,
                        chunks=point_count,
                        graph_facts=graph_result.fact_count,
                        graph_seconds=round(graph_seconds, 3),
                        graph_extraction_seconds=extraction_seconds,
                        extraction_splits=extraction_splits,
                        activated=activated,
                        seconds=round(time.monotonic() - started, 3),
                        counts=asdict(counts),
                    )
                    if only_work_id is not None:
                        target_work_done = True
                        break
                except Exception as exc:  # record safe exception type; source text is never logged
                    counts.errors += 1
                    counts.failed += 1
                    localized = (
                        failed_at == "graph_extraction_neo4j_projection"
                        and isinstance(exc, InferenceProtocolError | GraphExtractionError)
                    )
                    fatal = (
                        not localized
                        or isinstance(exc, SQLAlchemyError | httpx.HTTPError)
                        or type(exc).__module__.startswith("neo4j")
                    )
                    if fatal:
                        counts.fatal_errors += 1
                    failure = {
                        "work_id": source_document.external_id,
                        "stage": failed_at,
                        "error_type": type(exc).__name__,
                        "classification": "document_error" if localized and not fatal else "fatal",
                    }
                    failures = checkpoint.state.setdefault("failures", []) if checkpoint else None
                    if failures is not None:
                        failures.append(failure)
                    if checkpoint:
                        checkpoint.state.update(
                            cursor=page_cursor,
                            completed=sorted(completed),
                            counts=asdict(counts),
                        )
                        checkpoint.save()
                    self._event(
                        "document_failed",
                        work_id=source_document.external_id,
                        error=type(exc).__name__,
                        detail=(
                            str(exc) if type(exc).__module__ == "app.domain.inference" else None
                        ),
                        failed_at=failed_at,
                        classification=failure["classification"],
                        counts=asdict(counts),
                    )
                    if fatal:
                        halted = True
                        break
            if only_work_id is not None:
                if target_work_done or halted:
                    break
                if next_cursor is None:
                    counts.errors += 1
                    counts.failed += 1
                    self._event("target_not_found", work_id=only_work_id)
                    halted = True
                    break
                cursor = next_cursor
                if checkpoint:
                    checkpoint.state.update(
                        cursor=cursor, completed=sorted(completed), counts=asdict(counts)
                    )
                    checkpoint.save()
                continue
            if halted:
                break
            cursor = next_cursor
            if checkpoint:
                checkpoint.state.update(
                    cursor=cursor, completed=sorted(completed), counts=asdict(counts)
                )
                checkpoint.save()
        if checkpoint:
            checkpoint.state.update(
                cursor=cursor,
                completed=sorted(completed),
                counts=asdict(counts),
            )
            checkpoint.save()
        counts.wall_seconds = round(time.monotonic() - run_started, 3)
        self._event(
            "run_complete",
            counts=asdict(counts),
            docs_per_minute=round(
                (counts.activated + counts.previewed) * 60 / max(counts.wall_seconds, 0.001), 2
            ),
            dry_run=dry_run,
            status=(
                "failed"
                if halted
                else (
                    "completed_with_document_errors"
                    if counts.errors > errors_at_start
                    else "completed"
                )
            ),
        )
        return counts


def _build_runner(run_id: str, source: str) -> tuple[CorpusPilot, list[Any]]:
    required = ("DATABASE_URL", "QDRANT_URL", "NEO4J_PASSWORD", "INFERENCE_BASE_URL")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"missing environment settings: {', '.join(missing)}")
    config_path = Path(os.getenv("MODEL_CONFIG_PATH", "config/models.yaml"))
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    graph_config = config["generation"]["graph_extractor"]
    embedding_config = config["embedding"]
    namespace = os.getenv("EMBEDDING_NAMESPACE", "article-analysis-v1")
    graph_namespace = os.getenv("GRAPH_NAMESPACE", "article-analysis-domain-v1")
    http = httpx.AsyncClient(
        base_url=os.environ["INFERENCE_BASE_URL"], timeout=httpx.Timeout(600, connect=10)
    )
    openalex_http = httpx.AsyncClient(timeout=30)
    qdrant_http = httpx.AsyncClient(base_url=os.environ["QDRANT_URL"], timeout=60)
    engine = make_engine(os.environ["DATABASE_URL"])
    sessions = make_session_factory(engine)
    gate = GenerationGate(waiting_capacity=0)
    provider = OllamaProvider(
        cast(httpx.AsyncClient, _NonThinkingClient(http)),
        gate=gate,
        model_revisions={graph_config["model_id"]: graph_config["digest"]},
        supported_efforts={graph_config["model_id"]: set(graph_config["reasoning_efforts"])},
        embedding_batch_size=embedding_config["batch_size"],
    )
    embedding_spec = EmbeddingSpec.from_config(namespace, config_path)
    qdrant = QdrantIndex(qdrant_http, embedding_spec)
    driver = AsyncGraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]),
    )
    graph = Neo4jGraph(driver, namespace=graph_namespace)
    extractor = InferenceGraphExtractor(
        provider,
        model_id=graph_config["model_id"],
        model_revision=graph_config["digest"],
        timeout=graph_config["timeout_seconds"],
        max_output_tokens=graph_config["max_output_tokens"],
        context_window=graph_config["context_window"],
    )
    graph_index = GraphIndexingService(sessions, graph, extractor)
    openalex = OpenAlexClient.from_environment(openalex_http)
    epo_http = httpx.AsyncClient(timeout=30)
    epo = EpoOpsClient.from_environment(epo_http)
    pilot = CorpusPilot(
        client=openalex if source == "openalex" else epo,
        source=source,
        session_factory=sessions,
        qdrant=qdrant,
        embedder=provider,
        graph_index=graph_index,
        run_id=run_id,
    )
    return pilot, [openalex_http, epo_http, qdrant_http, http, graph, engine]


async def _preflight_runtime() -> None:
    """Verify configured stores and inference endpoint before the first persistent write."""
    required = ("DATABASE_URL", "QDRANT_URL", "NEO4J_PASSWORD", "INFERENCE_BASE_URL")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"missing environment settings: {', '.join(missing)}")

    engine = make_engine(os.environ["DATABASE_URL"])
    try:
        await asyncio.to_thread(_check_database, engine)
    except Exception as exc:
        raise RuntimeError("runtime preflight failed: postgres unavailable") from exc
    finally:
        engine.dispose()

    config_path = Path(os.getenv("MODEL_CONFIG_PATH", "config/models.yaml"))
    namespace = os.getenv("EMBEDDING_NAMESPACE", "article-analysis-v1")
    embedding_spec = EmbeddingSpec.from_config(namespace, config_path)
    async with httpx.AsyncClient(timeout=5) as client:
        for name, url in (
            ("qdrant", f"{os.environ['QDRANT_URL'].rstrip('/')}/collections"),
            ("inference", f"{os.environ['INFERENCE_BASE_URL'].rstrip('/')}/api/tags"),
        ):
            try:
                response = await client.get(url)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise RuntimeError(f"runtime preflight failed: {name} unavailable") from exc
            if name == "qdrant":
                try:
                    collections = response.json()["result"]["collections"]
                    if not isinstance(collections, list):
                        raise ValueError("invalid collection list")
                    if any(item.get("name") == embedding_spec.collection for item in collections):
                        detail = await client.get(
                            f"{os.environ['QDRANT_URL'].rstrip('/')}/collections/"
                            f"{embedding_spec.collection}"
                        )
                        detail.raise_for_status()
                        vectors = detail.json()["result"]["config"]["params"]["vectors"]
                        if (
                            vectors.get("size") != embedding_spec.dimension
                            or vectors.get("distance") != "Cosine"
                        ):
                            raise ValueError("vector configuration mismatch")
                except (KeyError, TypeError, ValueError, httpx.HTTPError) as exc:
                    raise RuntimeError(
                        "runtime preflight failed: qdrant collection identity mismatch"
                    ) from exc
            if name == "inference":
                try:
                    payload = response.json()
                    models = payload["models"]
                    if not isinstance(models, list):
                        raise ValueError("invalid model list")
                    available = {
                        item.get("name") or item.get("model"): item.get("digest")
                        for item in models
                        if isinstance(item, dict)
                    }
                    model_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
                    expected_models = (
                        model_config["generation"]["graph_extractor"],
                        model_config["embedding"],
                    )
                    for expected in expected_models:
                        actual_digest = available.get(expected["model_id"])
                        if actual_digest != expected["digest"]:
                            raise ValueError("configured model identity is unavailable")
                except (KeyError, TypeError, ValueError, OSError) as exc:
                    raise RuntimeError(
                        "runtime preflight failed: inference model identity mismatch"
                    ) from exc

    driver = AsyncGraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]),
    )
    try:
        await driver.verify_connectivity()
    except Exception as exc:
        raise RuntimeError(
            "runtime preflight failed: neo4j unavailable or authentication failed"
        ) from exc
    finally:
        await driver.close()


def _check_database(engine: Any) -> None:
    from sqlalchemy import text

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


async def _run_source(
    args: argparse.Namespace,
    *,
    source: str,
    max_documents: int,
    checkpoint_path: Path,
    run_id: str,
) -> tuple[RunCounts, dict[str, Any], str]:
    if not args.dry_run:
        await _preflight_runtime()
    config_path = Path(os.getenv("MODEL_CONFIG_PATH", "config/models.yaml"))
    checkpoint = Checkpoint(
        checkpoint_path,
        _run_identity(
            args.query,
            args.filter,
            config_path,
            source=source,
            max_documents=max_documents,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        ),
        persist=not args.dry_run,
    )
    checkpoint.load(resume=args.resume, run_id=(args.run_id if args.resume else run_id))
    if args.resume and not args.run_id:
        run_id = str(checkpoint.state["run_id"])
    if args.dry_run:
        async with httpx.AsyncClient(timeout=30) as source_http:
            source_client = (
                OpenAlexClient.from_environment(source_http)
                if source == "openalex"
                else EpoOpsClient.from_environment(source_http)
            )
            pilot = CorpusPilot(
                client=source_client,
                source=source,
                session_factory=None,
                qdrant=cast(QdrantIndex, None),
                embedder=None,
                graph_index=cast(GraphIndexingService, None),
                run_id=run_id,
            )
            counts = await pilot.run(
                query=args.query,
                max_documents=max_documents,
                dry_run=True,
                checkpoint=checkpoint,
                batch_size=args.batch_size,
                filters=args.filter,
                only_work_id=getattr(args, "only_work_id", None),
            )
    else:
        pilot, resources = _build_runner(run_id, source)
        try:
            counts = await pilot.run(
                query=args.query,
                max_documents=max_documents,
                dry_run=False,
                checkpoint=checkpoint,
                batch_size=args.batch_size,
                filters=args.filter,
                only_work_id=getattr(args, "only_work_id", None),
            )
        finally:
            for resource in resources:
                close = getattr(resource, "aclose", None) or getattr(resource, "close", None)
                if close:
                    value = close()
                    if asyncio.iscoroutine(value):
                        await value
    return counts, checkpoint.identity, run_id


async def _run(args: argparse.Namespace) -> int:
    run_id = args.run_id or f"corpus-{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"
    epo_configured = bool(os.getenv("EPO_CONSUMER_KEY") and os.getenv("EPO_CONSUMER_SECRET"))
    if args.source == "epo" and not epo_configured:
        report = {
            "run_id": run_id,
            "source": "epo",
            "status": "skipped",
            "reason": "credentials_not_configured",
            "dry_run": args.dry_run,
            "updated_at": _now(),
        }
        print(json.dumps({"stage": "source_skipped", **report}, ensure_ascii=False))
        if args.stats_output and not args.dry_run:
            output = Path(args.stats_output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return 0
    if args.source == "all" and args.filter:
        raise ValueError(
            "--filter uses source-native syntax; run OpenAlex and EPO separately to filter both"
        )
    sources = [args.source] if args.source != "all" else ["openalex", "epo"]
    skipped_sources: dict[str, str] = {}
    if args.source == "all" and not epo_configured:
        sources = ["openalex"]
        skipped_sources["epo"] = "credentials_not_configured"
        print(
            json.dumps(
                {"stage": "source_skipped", "source": "epo", "reason": skipped_sources["epo"]}
            )
        )
    if args.source == "all" and len(sources) == 2:
        half = (args.max_documents + 1) // 2
        allocations = {"openalex": half, "epo": args.max_documents - half}
        sources = [source for source in sources if allocations[source] > 0]
    else:
        allocations = {sources[0]: args.max_documents}

    totals = RunCounts()
    new_errors = 0
    new_fatal_errors = 0
    identities: dict[str, Any] = {}
    for source in sources:
        checkpoint_path = Path(args.checkpoint)
        if args.source == "all":
            checkpoint_path = checkpoint_path.with_name(
                f"{checkpoint_path.stem}.{source}{checkpoint_path.suffix}"
            )
        previous_errors = 0
        previous_fatal_errors = 0
        if args.resume and checkpoint_path.exists():
            previous_state = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            previous_errors = int(previous_state.get("counts", {}).get("errors", 0))
            previous_fatal_errors = int(previous_state.get("counts", {}).get("fatal_errors", 0))
        counts, identity, run_id = await _run_source(
            args,
            source=source,
            max_documents=allocations[source],
            checkpoint_path=checkpoint_path,
            run_id=run_id,
        )
        new_errors += max(0, counts.errors - previous_errors)
        new_fatal_errors += max(0, counts.fatal_errors - previous_fatal_errors)
        identities[source] = identity
        for name, value in asdict(counts).items():
            setattr(totals, name, getattr(totals, name) + value)
    status = (
        "failed"
        if new_fatal_errors
        else ("completed_with_document_errors" if new_errors else "completed")
    )
    stats = {
        "run_id": run_id,
        "source": args.source,
        "identities": identities,
        "requested_documents": args.max_documents,
        "counts": asdict(totals),
        "errors_this_run": new_errors,
        "fatal_errors_this_run": new_fatal_errors,
        "docs_per_minute": round(
            (totals.activated + totals.previewed) * 60 / max(totals.wall_seconds, 0.001), 2
        ),
        "skipped_sources": skipped_sources,
        "dry_run": args.dry_run,
        "status": status,
        "updated_at": _now(),
    }
    if args.stats_output and not args.dry_run:
        Path(args.stats_output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.stats_output).write_text(
            json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    elif args.stats_output and args.dry_run:
        print(
            json.dumps(
                {"stage": "stats_not_written", "reason": "dry_run_has_no_persistent_writes"}
            )
        )
    return 1 if new_fatal_errors else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["openalex", "epo", "all"], required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--filter")
    parser.add_argument("--max-documents", type=int, required=True)
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--checkpoint", default="data/checkpoints/corpus-backfill.json")
    parser.add_argument("--stats-output")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--only-work-id", help="Resume only this OpenAlex work, then stop")
    args = parser.parse_args()
    if not 1 <= args.max_documents <= 100:
        parser.error("--max-documents must be between 1 and 100")
    if not 1 <= args.batch_size <= 100:
        parser.error("--batch-size must be between 1 and 100")
    if args.only_work_id and (args.source != "openalex" or not args.resume):
        parser.error("--only-work-id requires --source openalex and --resume")
    try:
        sys.exit(asyncio.run(_run(args)))
    except KeyboardInterrupt:
        resume_args = (
            "python scripts/corpus_backfill.py "
            f"--source {args.source} --query {shlex.quote(args.query)} "
            f"--max-documents {args.max_documents} --batch-size {args.batch_size} "
            f"--checkpoint {shlex.quote(args.checkpoint)}"
        )
        if args.filter:
            resume_args += f" --filter {shlex.quote(args.filter)}"
        if args.run_id:
            resume_args += f" --run-id {shlex.quote(args.run_id)}"
        if args.only_work_id:
            resume_args += f" --only-work-id {shlex.quote(args.only_work_id)}"
        print(
            json.dumps(
                {
                    "stage": "interrupted",
                    "resume_command": f"{resume_args} --resume",
                }
            ),
            file=sys.stderr,
        )
        sys.exit(130)
    except Exception as exc:
        detail = str(exc) if isinstance(exc, ValueError | RuntimeError) else None
        print(
            json.dumps({"stage": "fatal", "error": type(exc).__name__, "detail": detail}),
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
