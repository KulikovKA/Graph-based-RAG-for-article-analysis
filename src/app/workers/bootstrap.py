"""Environment wiring and process lifecycle for the durable analysis worker."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import signal
from pathlib import Path

import httpx
import yaml
from neo4j import AsyncGraphDatabase
from sqlalchemy import text

from app.domain.planner import IntentPlanner
from app.integrations.inference_http import OllamaProvider
from app.integrations.neo4j import Neo4jGraph
from app.integrations.qdrant import EmbeddingSpec, QdrantIndex
from app.integrations.reranker_local import LocalQwenReranker
from app.services.analysis_run import AnalysisRunConfig, AnalysisRunService
from app.services.analyst import Analyst
from app.services.evidence_pack import GemmaTokenCounter
from app.services.retrieval import CandidateRetrievalService
from app.storage.repositories import make_engine, make_session_factory
from app.workers.analysis import AnalysisWorker, AnalysisWorkerConfig
from app.workers.inference import GenerationGate

logger = logging.getLogger(__name__)


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"required worker setting is missing: {name}")
    return value


def _positive_float(name: str, default: float) -> float:
    value = float(os.environ.get(name, default))
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def build_worker() -> tuple[AnalysisWorker, list[object]]:
    """Build the pinned local pipeline and return resources that need closing."""
    database_url = _required("DATABASE_URL")
    config_path = Path(os.environ.get("MODEL_CONFIG_PATH", "config/models.yaml"))
    model_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    planner_config = model_config["generation"]["planner"]
    analyst_config = model_config["generation"]["analyst"]
    embedding_config = model_config["embedding"]
    reranker_config = model_config["reranker"]

    engine = make_engine(database_url)
    session_factory = make_session_factory(engine)
    if not Path(_required("ANALYST_TOKENIZER_PATH")).is_file():
        raise RuntimeError("pinned Analyst tokenizer file is unavailable")
    tokenizer = GemmaTokenCounter.from_file(
        Path(os.environ["ANALYST_TOKENIZER_PATH"]),
        expected_sha256=analyst_config["tokenizer"]["file_sha256"],
    )

    reranker = LocalQwenReranker(
        model_id=reranker_config["model_id"],
        model_path=Path(_required("RERANKER_MODEL_PATH")),
        max_length=reranker_config["max_length"],
    )
    gate = GenerationGate(waiting_capacity=0)
    inference_client = httpx.AsyncClient(
        base_url=_required("INFERENCE_BASE_URL"),
        timeout=httpx.Timeout(600, connect=10),
    )
    provider = OllamaProvider(
        inference_client,
        gate=gate,
        model_revisions={
            planner_config["model_id"]: planner_config["digest"],
            analyst_config["model_id"]: analyst_config["digest"],
        },
        supported_efforts={
            planner_config["model_id"]: set(planner_config["reasoning_efforts"]),
            analyst_config["model_id"]: set(analyst_config["reasoning_efforts"]),
        },
        reranker=reranker,
        embedding_batch_size=embedding_config["batch_size"],
    )

    qdrant_client = httpx.AsyncClient(
        base_url=_required("QDRANT_URL"), timeout=httpx.Timeout(60, connect=5)
    )
    embedding_spec = EmbeddingSpec.from_config(
        os.environ.get("EMBEDDING_NAMESPACE", "article-analysis-v1"), config_path
    )
    qdrant = QdrantIndex(qdrant_client, embedding_spec)
    neo4j_driver = AsyncGraphDatabase.driver(
        _required("NEO4J_URI"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), _required("NEO4J_PASSWORD")),
    )
    graph = Neo4jGraph(
        neo4j_driver,
        namespace=os.environ.get("GRAPH_NAMESPACE", "article-analysis-domain-v1"),
    )
    retrieval = CandidateRetrievalService(
        session_factory,
        qdrant,
        provider,
        graph,
        graph_namespace=graph.namespace,
        graph_vocabulary_version=os.environ.get("GRAPH_VOCABULARY_VERSION", "technical-feature-v1"),
    )
    planner = IntentPlanner(
        provider,
        model_id=planner_config["model_id"],
        prompt=Path("prompts/planner_v1.txt").read_text(encoding="utf-8"),
    )
    analyst = Analyst(provider, model_id=analyst_config["model_id"])

    async def score_documents(
        query: str,
        documents: list[str],
        request_id: str,
        timeout: float,
        cancel: asyncio.Event,
    ) -> list[float]:
        return await provider.rerank(
            model_id=reranker_config["model_id"],
            request_id=request_id,
            query=query,
            documents=documents,
            timeout=timeout,
            cancel=cancel,
        )

    retrieval_identity = {
        "embedding": embedding_spec.projection_version,
        "graph_namespace": graph.namespace,
        "graph_vocabulary_version": retrieval.graph_vocabulary_version,
        "retrieval_config": retrieval.config.__dict__,
        "reranker": f"{reranker_config['model_id']}@{reranker_config['revision']}",
    }
    retrieval_config_hash = hashlib.sha256(
        json.dumps(retrieval_identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    tokenizer_version = (
        f"{analyst_config['tokenizer']['repo_id']}@{analyst_config['tokenizer']['revision']}"
        f"#{analyst_config['tokenizer']['file_sha256']}"
    )
    service = AnalysisRunService(
        session_factory,
        planner,
        retrieval,
        analyst,
        rerank=score_documents,
        token_counter=tokenizer,
        retrieval_config_hash=retrieval_config_hash,
        analyst_tokenizer_version=tokenizer_version,
        config=AnalysisRunConfig(
            deadline_seconds=_positive_float("ANALYSIS_RUN_DEADLINE_SECONDS", 1800),
        ),
    )
    worker = AnalysisWorker(
        session_factory,
        service,
        config=AnalysisWorkerConfig(
            worker_id=os.environ.get("ANALYSIS_WORKER_ID", "analysis-worker-1"),
            lease_seconds=_positive_float("ANALYSIS_JOB_LEASE_SECONDS", 30),
            heartbeat_seconds=_positive_float("ANALYSIS_JOB_HEARTBEAT_SECONDS", 5),
            poll_seconds=_positive_float("ANALYSIS_JOB_POLL_SECONDS", 1),
            max_attempts=int(os.environ.get("ANALYSIS_JOB_MAX_ATTEMPTS", "3")),
        ),
    )
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    resources: list[object] = [reranker, inference_client, qdrant_client, graph, engine]
    return worker, resources


async def _close(resources: list[object]) -> None:
    for resource in resources:
        close = getattr(resource, "close", None) or getattr(resource, "aclose", None)
        if not callable(close):
            dispose = getattr(resource, "dispose", None)
            if callable(dispose):
                dispose()
            continue
        result = close()
        if asyncio.iscoroutine(result):
            await result


async def _serve() -> None:
    ready_path = Path("/tmp/worker.ready")
    ready_path.unlink(missing_ok=True)
    worker, resources = build_worker()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(signum, worker.stop)
    ready_path.touch()
    logger.info("analysis_worker_ready")
    try:
        await worker.run_forever()
    finally:
        ready_path.unlink(missing_ok=True)
        await _close(resources)


def main() -> None:
    logging.basicConfig(level=os.environ.get("APP_LOG_LEVEL", "INFO"))
    asyncio.run(_serve())


if __name__ == "__main__":
    main()
