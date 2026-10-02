"""Opt-in smoke test against the configured PostgreSQL/Qdrant/Neo4j/Ollama runtime."""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path

import httpx
import pytest
import yaml
from neo4j import AsyncGraphDatabase
from sqlalchemy import select, text

from app.domain.inference import InferenceProvider
from app.integrations.inference_http import OllamaProvider
from app.integrations.neo4j import CanonicalNeo4jProjection
from app.integrations.qdrant import FeatureEmbeddingIndex, FeatureEmbeddingSpec, FeatureVectorPoint
from app.services.feature_equivalence import FeatureEquivalenceClassifier
from app.storage.models import CanonicalizationRun
from app.storage.repositories import make_engine, make_session_factory
from app.workers.inference import GenerationGate

pytestmark = pytest.mark.skipif(
    os.getenv("GRAPH002_INTEGRATION") != "1",
    reason="set GRAPH002_INTEGRATION=1 to use the configured local stores and inference models",
)


def test_graph002_shadow_connectors_and_pinned_models() -> None:
    required = (
        "DATABASE_URL",
        "QDRANT_URL",
        "NEO4J_URI",
        "NEO4J_PASSWORD",
        "INFERENCE_BASE_URL",
    )
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        pytest.fail(f"missing integration settings: {', '.join(missing)}")
    config_path = Path(os.getenv("MODEL_CONFIG_PATH", "config/models.yaml"))
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    embedding = config["embedding"]
    classifier_config = config["generation"]["relation_classifier"]
    run_id = uuid.uuid4()
    resolver_version = f"graph002-integration-{run_id.hex[:8]}"
    feature_spec = FeatureEmbeddingSpec.from_config(resolver_version, config_path)
    graph_namespace = os.getenv("GRAPH_NAMESPACE", "article-analysis-domain-v1")
    canonical_id = str(uuid.uuid4())
    document_key = f"{graph_namespace}:work:graph002-integration-{run_id}:rev:{run_id}"

    async def run() -> None:
        database_url = os.environ["DATABASE_URL"]
        engine = make_engine(database_url)
        sessions = make_session_factory(engine)
        with sessions() as session:
            assert session.scalar(select(text("1"))) == 1
            session.scalars(select(CanonicalizationRun).limit(1)).all()

        inference_client = httpx.AsyncClient(
            base_url=os.environ["INFERENCE_BASE_URL"], timeout=httpx.Timeout(300, connect=10)
        )
        qdrant_client = httpx.AsyncClient(
            base_url=os.environ["QDRANT_URL"], timeout=httpx.Timeout(60, connect=10)
        )
        driver = AsyncGraphDatabase.driver(
            os.environ["NEO4J_URI"],
            auth=(os.getenv("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]),
        )
        provider: InferenceProvider = OllamaProvider(
            inference_client,
            gate=GenerationGate(waiting_capacity=0),
            model_revisions={
                embedding["model_id"]: embedding["digest"],
                classifier_config["model_id"]: classifier_config["digest"],
            },
            supported_efforts={classifier_config["model_id"]: set()},
            embedding_batch_size=16,
        )
        index = FeatureEmbeddingIndex(qdrant_client, feature_spec)
        collection_created = False
        projected = False
        try:
            tags = (await inference_client.get("/api/tags", timeout=10)).json()["models"]
            installed = {item["name"]: item["digest"] for item in tags}
            assert installed[embedding["model_id"]] == embedding["digest"]
            assert installed[classifier_config["model_id"]] == classifier_config["digest"]
            await index.ensure_collection()
            collection_created = True
            vectors = await provider.embed(
                model_id=embedding["model_id"],
                request_id=f"{run_id}:integration-embedding",
                texts=["room temperature"],
                timeout=180,
            )
            await index.upsert(
                [
                    FeatureVectorPoint(
                        normalized_feature_text="room temperature",
                        raw_feature_text="room-temperature",
                        feature_key="graph002-integration-feature",
                        run_id=run_id,
                        document_count=1,
                        vector=vectors[0],
                    )
                ]
            )
            hits = await index.query(vectors[0], run_id=run_id, limit=1)
            assert hits and hits[0].normalized_feature_text == "room temperature"

            classifier = FeatureEquivalenceClassifier(
                inference_client,
                model_id=classifier_config["model_id"],
                digest=classifier_config["digest"],
                max_state_bytes=classifier_config.get("max_state_bytes", 6000),
            )
            decision = await classifier.classify(
                feature_a="room temperature",
                feature_b="room-temperature",
                context_a="The sensor operates at room temperature.",
                context_b="Operation is conducted at room-temperature conditions.",
                request_id=f"{run_id}:integration-classifier",
                timeout=180,
            )
            assert decision.decision in {"SAME", "DIFFERENT", "UNCERTAIN"}
            projection = CanonicalNeo4jProjection(driver, namespace=graph_namespace)
            count = await projection.project(
                run_id=run_id,
                resolver_version=resolver_version,
                rows=[
                    {
                        "document_label": "ScientificWork",
                        "document_key": document_key,
                        "canonical_feature_id": canonical_id,
                        "canonical_text": "graph002 integration feature",
                        "member_count": 1,
                        "document_count": 1,
                        "evidence_count": 2,
                    }
                ],
            )
            projected = count == 1
            assert projected
        finally:
            if projected:
                async with driver.session(database=os.getenv("NEO4J_DATABASE", "neo4j")) as session:
                    result = await session.run(
                        "MATCH (document:ScientificWork {key: $key})-"
                        "[edge:DISCLOSES_CANONICAL_FEATURE {run_id: $run_id}]->"
                        "(feature:CanonicalTechnicalFeature {canonical_feature_id: $canonical_id}) "
                        "DELETE edge DETACH DELETE document DETACH DELETE feature",
                        key=document_key,
                        run_id=str(run_id),
                        canonical_id=canonical_id,
                    )
                    await result.consume()
            if collection_created:
                await qdrant_client.delete(f"/collections/{feature_spec.collection}")
            await driver.close()
            await inference_client.aclose()
            await qdrant_client.aclose()
            engine.dispose()

    asyncio.run(run())
