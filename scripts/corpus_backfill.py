"""Bounded corpus ingestion through the production document and index services."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
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

from app.domain.source import ScientificWork, SourceStatus
from app.integrations.inference_http import OllamaProvider
from app.integrations.neo4j import PROJECTION_VERSION, Neo4jGraph
from app.integrations.openalex import OpenAlexClient
from app.integrations.qdrant import EmbeddingSpec, QdrantIndex
from app.services.graph_index import (
    EXTRACTOR_VERSION,
    GraphIndexingService,
    InferenceGraphExtractor,
)
from app.services.indexing import IndexingService
from app.services.ingestion import IngestionService
from app.storage.repositories import make_engine, make_session_factory
from app.workers.inference import GenerationGate
from app.workers.ingest import from_openalex


@dataclass
class RunCounts:
    fetched: int = 0
    skipped: int = 0
    ingested: int = 0
    indexed: int = 0
    graph_projected: int = 0
    errors: int = 0


class Checkpoint:
    """Atomically persisted cursor and run identity; reject unsafe resume drift."""

    def __init__(self, path: Path, identity: dict[str, Any]) -> None:
        self.path = path
        self.identity = identity
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
    max_documents: int,
    batch_size: int,
    dry_run: bool,
) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    embedding = config["embedding"]
    graph = config["generation"]["graph_extractor"]
    identity = {
        "source": "openalex",
        "query": query,
        "filter": filters,
        "max_documents": max_documents,
        "batch_size": batch_size,
        "dry_run": dry_run,
        "embedding_model": embedding["model_id"],
        "embedding_digest": embedding["digest"],
        "dimension": embedding["dimension"],
        "graph_model": graph["model_id"],
        "graph_digest": graph["digest"],
        "extractor_version": graph["extractor_version"],
        "graph_output_tokens": graph["max_output_tokens"],
        "graph_projection_version": PROJECTION_VERSION,
        "graph_indexer_version": EXTRACTOR_VERSION,
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
        client: OpenAlexClient,
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
        self.session_factory = session_factory
        self.qdrant = qdrant
        self.embedder = embedder
        self.graph_index = graph_index
        self.run_id = run_id
        self.emit = emit

    def _event(self, stage: str, **values: Any) -> None:
        self.emit({"run_id": self.run_id, "stage": stage, **values})

    async def run(
        self,
        *,
        query: str,
        max_documents: int,
        dry_run: bool,
        checkpoint: Checkpoint | None = None,
        batch_size: int = 25,
        filters: str | None = None,
    ) -> RunCounts:
        counts = RunCounts(**(checkpoint.state.get("counts", {}) if checkpoint else {}))
        cursor: str | None = checkpoint.state.get("cursor", "*") if checkpoint else "*"
        seen: set[str] = set()
        completed = set(checkpoint.state.get("completed", [])) if checkpoint else set()
        halted = False
        while cursor and counts.ingested < max_documents:
            page_cursor = cursor
            page = await self.client.search(
                query, per_page=min(100, batch_size), cursor=page_cursor, filters=filters
            )
            if page.status != SourceStatus.OK:
                counts.errors += 1
                self._event("search_failed", status=page.status.value, error=page.error_code)
                break
            next_cursor = page.next_cursor
            for candidate in page.works:
                if counts.ingested >= max_documents:
                    break
                if candidate.external_id in seen:
                    continue
                seen.add(candidate.external_id)
                if candidate.external_id in completed:
                    continue
                fetched = await self.client.fetch(candidate.external_id)
                if fetched.status != SourceStatus.OK or not fetched.works:
                    counts.errors += 1
                    self._event(
                        "fetch_failed", work_id=candidate.external_id, error=fetched.error_code
                    )
                    halted = True
                    break
                work: ScientificWork = fetched.works[0]
                counts.fetched += 1
                if (
                    not work.title
                    or not work.title.strip()
                    or not work.abstract
                    or len(work.abstract.strip()) < 80
                ):
                    counts.skipped += 1
                    completed.add(work.external_id)
                    self._event(
                        "skipped",
                        work_id=work.external_id,
                        reason="insufficient_abstract",
                        counts=asdict(counts),
                    )
                    if checkpoint:
                        checkpoint.state.update(
                            cursor=page_cursor, completed=sorted(completed), counts=asdict(counts)
                        )
                        checkpoint.save()
                    continue
                if dry_run:
                    counts.ingested += 1
                    completed.add(work.external_id)
                    if checkpoint:
                        checkpoint.state.update(
                            cursor=page_cursor, completed=sorted(completed), counts=asdict(counts)
                        )
                        checkpoint.save()
                    self._event(
                        "would_ingest",
                        work_id=work.external_id,
                        title=work.title,
                        counts=asdict(counts),
                    )
                    continue
                started = time.monotonic()
                failed_at = "postgres_ingestion"
                try:
                    with self.session_factory.begin() as session:
                        revision, created = IngestionService(session).ingest(from_openalex(work))
                        revision_id = revision.id
                    failed_at = "qdrant_embedding_index"
                    with self.session_factory() as session:
                        embedder = _ProgressEmbedder(
                            self.embedder,
                            lambda event: self.emit({"run_id": self.run_id, **event}),
                            work.external_id,
                        )
                        qdrant_index = IndexingService(session, self.qdrant, embedder)
                        point_count = await qdrant_index.index_revision(
                            revision_id, request_id=f"{self.run_id}:{work.external_id}:qdrant"
                        )
                    qdrant_version = ("qdrant-indexer-v1", self.qdrant.spec.projection_version)
                    failed_at = "graph_extraction_neo4j_projection"
                    graph_result = await self.graph_index.index_revision(
                        revision_id, request_id=f"{self.run_id}:{work.external_id}:graph"
                    )
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
                    if not activated:
                        raise RuntimeError(
                            "required index acknowledgements did not activate revision"
                        )
                    counts.ingested += 1
                    counts.indexed += 1
                    counts.graph_projected += 1
                    completed.add(work.external_id)
                    if checkpoint:
                        checkpoint.state.update(
                            cursor=page_cursor,
                            completed=sorted(completed),
                            counts=asdict(counts),
                        )
                        checkpoint.save()
                    self._event(
                        "document_complete",
                        work_id=work.external_id,
                        title=work.title,
                        revision_id=str(revision_id),
                        new_revision=created,
                        chunks=point_count,
                        graph_facts=graph_result.fact_count,
                        activated=activated,
                        seconds=round(time.monotonic() - started, 3),
                        counts=asdict(counts),
                    )
                except Exception as exc:  # record safe exception type; source text is never logged
                    counts.errors += 1
                    if checkpoint:
                        checkpoint.state.update(
                            cursor=page_cursor,
                            completed=sorted(completed),
                            counts=asdict(counts),
                        )
                        checkpoint.save()
                    self._event(
                        "document_failed",
                        work_id=work.external_id,
                        error=type(exc).__name__,
                        detail=(
                            str(exc) if type(exc).__module__ == "app.domain.inference" else None
                        ),
                        failed_at=failed_at,
                        counts=asdict(counts),
                    )
                    halted = True
                    break
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
        self._event(
            "run_complete",
            counts=asdict(counts),
            dry_run=dry_run,
            status="failed" if halted or counts.errors else "completed",
        )
        return counts


def _build_runner(run_id: str) -> tuple[CorpusPilot, list[Any]]:
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
        max_output_tokens=graph_config["max_output_tokens"],
    )
    graph_index = GraphIndexingService(sessions, graph, extractor)
    openalex = OpenAlexClient.from_environment(openalex_http)
    pilot = CorpusPilot(
        client=openalex,
        session_factory=sessions,
        qdrant=qdrant,
        embedder=provider,
        graph_index=graph_index,
        run_id=run_id,
    )
    return pilot, [openalex_http, qdrant_http, http, graph, engine]


async def _run(args: argparse.Namespace) -> int:
    if args.source != "openalex":
        raise ValueError("this runner currently supports --source openalex")
    run_id = args.run_id or f"corpus-{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"
    config_path = Path(os.getenv("MODEL_CONFIG_PATH", "config/models.yaml"))
    checkpoint = Checkpoint(
        Path(args.checkpoint),
        _run_identity(
            args.query,
            args.filter,
            config_path,
            max_documents=args.max_documents,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        ),
    )
    checkpoint.load(resume=args.resume, run_id=(args.run_id if args.resume else run_id))
    if args.resume and not args.run_id:
        run_id = checkpoint.state["run_id"]
    if args.dry_run:
        async with httpx.AsyncClient(timeout=30) as source_http:
            pilot = CorpusPilot(
                client=OpenAlexClient.from_environment(source_http),
                session_factory=None,
                qdrant=cast(QdrantIndex, None),
                embedder=None,
                graph_index=cast(GraphIndexingService, None),
                run_id=run_id,
            )
            counts = await pilot.run(
                query=args.query,
                max_documents=args.max_documents,
                dry_run=True,
                checkpoint=checkpoint,
                batch_size=args.batch_size,
                filters=args.filter,
            )
    else:
        pilot, resources = _build_runner(run_id)
        try:
            counts = await pilot.run(
                query=args.query,
                max_documents=args.max_documents,
                dry_run=False,
                checkpoint=checkpoint,
                batch_size=args.batch_size,
                filters=args.filter,
            )
        finally:
            for resource in resources:
                close = getattr(resource, "aclose", None) or getattr(resource, "close", None)
                if close:
                    value = close()
                    if asyncio.iscoroutine(value):
                        await value
    if args.stats_output:
        stats = {
            "run_id": run_id,
            "identity": checkpoint.identity,
            "requested_documents": args.max_documents,
            "counts": asdict(counts),
            "dry_run": args.dry_run,
            "status": "failed" if counts.errors else "completed",
            "updated_at": _now(),
        }
        Path(args.stats_output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.stats_output).write_text(
            json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    return 1 if counts.errors else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["openalex"], required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--filter")
    parser.add_argument("--max-documents", type=int, required=True)
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--checkpoint", default="data/checkpoints/corpus-backfill.json")
    parser.add_argument("--stats-output")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-id")
    args = parser.parse_args()
    if not 1 <= args.max_documents <= 100:
        parser.error("--max-documents must be between 1 and 100")
    if not 1 <= args.batch_size <= 100:
        parser.error("--batch-size must be between 1 and 100")
    try:
        sys.exit(asyncio.run(_run(args)))
    except KeyboardInterrupt:
        print(
            json.dumps(
                {
                    "stage": "interrupted",
                    "resume_command": (
                        f"python scripts/corpus_backfill.py --source openalex --query "
                        f"{args.query!r} --max-documents {args.max_documents} "
                        f"--batch-size {args.batch_size} --checkpoint {args.checkpoint} --resume"
                    ),
                }
            ),
            file=sys.stderr,
        )
        sys.exit(130)
    except Exception as exc:
        detail = str(exc) if isinstance(exc, ValueError) else None
        print(
            json.dumps({"stage": "fatal", "error": type(exc).__name__, "detail": detail}),
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
