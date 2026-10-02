"""Namespace-ограниченная проекция долговечных фактов PostgreSQL в Neo4j."""

import asyncio
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from neo4j import AsyncDriver, AsyncManagedTransaction

from app.domain.graph import EDGE_ENDPOINTS, GraphEdgeType, GraphNodeLabel

_NAMESPACE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_MIGRATION_DIR = Path(__file__).resolve().parents[3] / "migrations" / "neo4j"
PROJECTION_VERSION = "domain-graph-v1"


@dataclass(frozen=True)
class GraphNode:
    label: GraphNodeLabel
    key: str
    properties: dict[str, Any]


@dataclass(frozen=True)
class ProjectedFact:
    fact_id: UUID
    source: GraphNode
    edge_type: GraphEdgeType
    target: GraphNode
    properties: dict[str, Any]

    def __post_init__(self) -> None:
        allowed_sources, allowed_targets = EDGE_ENDPOINTS[self.edge_type]
        if self.source.label not in allowed_sources or self.target.label not in allowed_targets:
            raise ValueError("graph edge endpoints do not match the ontology")


@dataclass(frozen=True)
class GraphEdgeRecord:
    source_key: str
    source_label: str
    edge_type: str
    target_key: str
    target_label: str
    properties: dict[str, Any]


class Neo4jGraph:
    """Выполняет фиксированные Cypher-шаблоны с типами из allowlist enum."""

    def __init__(
        self,
        driver: AsyncDriver,
        *,
        namespace: str = "article-analysis-domain-v1",
        database: str = "neo4j",
    ) -> None:
        if not _NAMESPACE.fullmatch(namespace):
            raise ValueError("invalid graph namespace")
        if not database or len(database) > 63:
            raise ValueError("invalid Neo4j database")
        self.driver = driver
        self.namespace = namespace
        self.database = database
        self._schema_ready = False
        self._schema_lock = asyncio.Lock()

    def _validate_key(self, key: str) -> None:
        if not key.startswith(f"{self.namespace}:"):
            raise ValueError("graph key is outside this namespace")

    async def ensure_schema(self) -> None:
        if self._schema_ready:
            return
        async with self._schema_lock:
            if self._schema_ready:
                return
            if not _MIGRATION_DIR.is_dir():
                raise RuntimeError("Neo4j migrations are unavailable")
            migrations = sorted(_MIGRATION_DIR.glob("*.cypher"))
            if not migrations:
                raise RuntimeError("Neo4j migrations are empty")
            async with self.driver.session(database=self.database) as session:
                for migration in migrations:
                    for statement in migration.read_text(encoding="utf-8").split(";"):
                        statement = statement.strip()
                        if statement:
                            result = await session.run(statement)
                            await result.consume()
            self._schema_ready = True

    @staticmethod
    def _node_query(label: GraphNodeLabel) -> str:
        return f"MERGE (node:{label.value} {{key: $key}}) SET node += $properties"

    @staticmethod
    def _fact_query(
        source_label: GraphNodeLabel,
        edge_type: GraphEdgeType,
        target_label: GraphNodeLabel,
    ) -> str:
        return f"""
        UNWIND $rows AS row
        MERGE (source:{source_label.value} {{key: row.source_key}})
        SET source += row.source_properties
        MERGE (target:{target_label.value} {{key: row.target_key}})
        SET target += row.target_properties
        MERGE (source)-[fact:{edge_type.value} {{fact_id: row.fact_id}}]->(target)
        SET fact += row.fact_properties
        RETURN count(fact) AS projected
        """

    async def upsert_revision(self, root: GraphNode, facts: list[ProjectedFact]) -> int:
        """Атомарно сохраняет проекцию ревизии; повтор безопасен по fact_id."""
        self._validate_key(root.key)
        if root.label not in {GraphNodeLabel.PATENT, GraphNodeLabel.SCIENTIFIC_WORK}:
            raise ValueError("revision root must be a public document node")
        if root.properties.get("namespace") != self.namespace:
            raise ValueError("revision root namespace mismatch")
        for fact in facts:
            self._validate_key(fact.source.key)
            self._validate_key(fact.target.key)
            if fact.source.key != root.key:
                raise ValueError("revision projection has an unrelated source node")
            if fact.source.properties.get("namespace") != self.namespace:
                raise ValueError("source node namespace mismatch")
            if fact.target.properties.get("namespace") != self.namespace:
                raise ValueError("target node namespace mismatch")

        await self.ensure_schema()
        groups: dict[tuple[GraphNodeLabel, GraphEdgeType, GraphNodeLabel], list[ProjectedFact]] = (
            defaultdict(list)
        )
        seen_fact_ids: set[UUID] = set()
        for fact in facts:
            if fact.fact_id in seen_fact_ids:
                raise ValueError("duplicate fact_id in graph projection")
            seen_fact_ids.add(fact.fact_id)
            groups[(fact.source.label, fact.edge_type, fact.target.label)].append(fact)

        async def write_revision(tx: AsyncManagedTransaction) -> int:
            root_result = await tx.run(
                self._node_query(root.label),
                key=root.key,
                properties={**root.properties, "key": root.key, "namespace": self.namespace},
            )
            await root_result.consume()
            projected = 0
            for (source_label, edge_type, target_label), grouped_facts in groups.items():
                rows = [
                    {
                        "fact_id": str(item.fact_id),
                        "source_key": item.source.key,
                        "target_key": item.target.key,
                        "source_properties": {
                            **item.source.properties,
                            "key": item.source.key,
                            "namespace": self.namespace,
                        },
                        "target_properties": {
                            **item.target.properties,
                            "key": item.target.key,
                            "namespace": self.namespace,
                        },
                        "fact_properties": {
                            **item.properties,
                            "fact_id": str(item.fact_id),
                            "namespace": self.namespace,
                        },
                    }
                    for item in grouped_facts
                ]
                result = await tx.run(
                    self._fact_query(source_label, edge_type, target_label), rows=rows
                )
                record = await result.single()
                await result.consume()
                if record is None or record["projected"] != len(grouped_facts):
                    raise RuntimeError("Neo4j graph projection is incomplete")
                projected += record["projected"]
            return projected

        async with self.driver.session(database=self.database) as session:
            return await session.execute_write(write_revision)

    async def remove_revision(self, revision_id: UUID) -> None:
        """Удаляет provenance этой ревизии и сохраняет общие узлы."""
        async with self.driver.session(database=self.database) as session:

            async def remove(tx: AsyncManagedTransaction) -> None:
                result = await tx.run(
                    """
                    MATCH ()-[fact]->()
                    WHERE fact.namespace = $namespace
                      AND fact.document_revision_id = $revision_id
                    DELETE fact
                    """,
                    namespace=self.namespace,
                    revision_id=str(revision_id),
                )
                await result.consume()
                result = await tx.run(
                    """
                    MATCH (document)
                    WHERE document.namespace = $namespace
                      AND document.revision_id = $revision_id
                      AND (document:Patent OR document:ScientificWork)
                    DETACH DELETE document
                    """,
                    namespace=self.namespace,
                    revision_id=str(revision_id),
                )
                await result.consume()

            await session.execute_write(remove)

    async def one_hop(self, key: str, *, limit: int = 50) -> list[GraphEdgeRecord]:
        """Возвращает один hop в namespace с жёстким лимитом результата."""
        self._validate_key(key)
        if not 1 <= limit <= 100:
            raise ValueError("graph traversal limit must be between 1 and 100")
        query = """
        MATCH (origin {key: $key, namespace: $namespace})-[relationship]-(neighbor)
        WHERE neighbor.namespace = $namespace
          AND type(relationship) IN $edge_types
        RETURN startNode(relationship).key AS source_key,
               labels(startNode(relationship)) AS source_labels,
               type(relationship) AS edge_type,
               endNode(relationship).key AS target_key,
               labels(endNode(relationship)) AS target_labels,
               properties(relationship) AS properties
        LIMIT $limit
        """
        async with self.driver.session(database=self.database) as session:
            result = await session.run(
                query,
                key=key,
                namespace=self.namespace,
                edge_types=[item.value for item in GraphEdgeType],
                limit=limit,
            )
            records = await result.data()
            await result.consume()
        return [
            GraphEdgeRecord(
                source_key=record["source_key"],
                source_label=record["source_labels"][0],
                edge_type=record["edge_type"],
                target_key=record["target_key"],
                target_label=record["target_labels"][0],
                properties=dict(record["properties"]),
            )
            for record in records
        ]

    async def close(self) -> None:
        await self.driver.close()


class CanonicalNeo4jProjection:
    """Additive GRAPH-002 shadow projection; never mutates baseline feature edges."""

    def __init__(
        self,
        driver: AsyncDriver,
        *,
        namespace: str = "article-analysis-domain-v1",
        database: str = "neo4j",
    ) -> None:
        if not _NAMESPACE.fullmatch(namespace):
            raise ValueError("invalid graph namespace")
        if not database or len(database) > 63:
            raise ValueError("invalid Neo4j database")
        self.driver = driver
        self.namespace = namespace
        self.database = database
        self._schema_ready = False
        self._schema_lock = asyncio.Lock()

    async def ensure_schema(self) -> None:
        if self._schema_ready:
            return
        async with self._schema_lock:
            if self._schema_ready:
                return
            async with self.driver.session(database=self.database) as session:
                result = await session.run(
                    "CREATE CONSTRAINT uq_graph002_canonical_feature_id IF NOT EXISTS "
                    "FOR (feature:CanonicalTechnicalFeature) "
                    "REQUIRE feature.canonical_feature_id IS UNIQUE"
                )
                await result.consume()
            self._schema_ready = True

    async def project(
        self,
        *,
        run_id: UUID,
        resolver_version: str,
        rows: list[dict[str, Any]],
    ) -> int:
        if not resolver_version or len(resolver_version) > 128:
            raise ValueError("invalid resolver version")
        if any(item.get("document_label") not in {"Patent", "ScientificWork"} for item in rows):
            raise ValueError("canonical projection contains an unsupported document label")
        for item in rows:
            document_key = item.get("document_key")
            if not isinstance(document_key, str) or not document_key.startswith(
                f"{self.namespace}:"
            ):
                raise ValueError("canonical projection document is outside this namespace")
            feature_id = item.get("canonical_feature_id")
            if not isinstance(feature_id, str) or not item.get("canonical_text"):
                raise ValueError("canonical projection feature identity is incomplete")
            if int(item.get("evidence_count", 0)) < 1:
                raise ValueError("canonical projection evidence_count must be positive")
        await self.ensure_schema()

        async def write(
            tx: AsyncManagedTransaction, label: str, grouped: list[dict[str, Any]]
        ) -> int:
            query = f"""
            UNWIND $rows AS row
            MERGE (document:{label} {{key: row.document_key}})
            MERGE (feature:CanonicalTechnicalFeature {{
              canonical_feature_id: row.canonical_feature_id
            }})
            SET feature += row.feature_properties
            MERGE (document)-[edge:DISCLOSES_CANONICAL_FEATURE {{run_id: row.run_id}}]->(feature)
            SET edge.resolver_version = row.resolver_version,
                edge.evidence_count = row.evidence_count,
                edge.namespace = $namespace
            RETURN count(edge) AS projected
            """
            result = await tx.run(
                query,
                rows=grouped,
                namespace=self.namespace,
            )
            record = await result.single()
            await result.consume()
            projected = int(record["projected"]) if record else 0
            if projected != len(grouped):
                raise RuntimeError("Neo4j canonical shadow projection is incomplete")
            return projected

        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in rows:
            groups[str(item["document_label"])].append(
                {
                    "document_key": item["document_key"],
                    "canonical_feature_id": item["canonical_feature_id"],
                    "run_id": str(run_id),
                    "resolver_version": resolver_version,
                    "evidence_count": int(item["evidence_count"]),
                    "feature_properties": {
                        "canonical_feature_id": item["canonical_feature_id"],
                        "canonical_text": item["canonical_text"],
                        "resolver_version": resolver_version,
                        "member_count": int(item["member_count"]),
                        "document_count": int(item["document_count"]),
                        "run_id": str(run_id),
                        "namespace": self.namespace,
                    },
                }
            )
        async with self.driver.session(database=self.database) as session:

            async def write_all(tx: AsyncManagedTransaction) -> int:
                total = 0
                for label in ("Patent", "ScientificWork"):
                    if groups.get(label):
                        total += await write(tx, label, groups[label])
                return total

            return await session.execute_write(write_all)
