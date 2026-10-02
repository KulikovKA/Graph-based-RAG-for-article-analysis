"""Small Qdrant REST adapter for the product's revision-scoped vector projection."""

import hashlib
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

import httpx
import yaml


@dataclass(frozen=True)
class EmbeddingSpec:
    namespace: str
    model_id: str
    model_version: str
    dimension: int

    def __post_init__(self) -> None:
        if not all((self.namespace, self.model_id, self.model_version)):
            raise ValueError("embedding namespace, model and version are required")
        if self.dimension < 1:
            raise ValueError("embedding dimension must be positive")

    @property
    def collection(self) -> str:
        prefix = re.sub(r"[^a-z0-9_]+", "_", self.namespace.lower()).strip("_")[:24]
        if not prefix:
            raise ValueError("embedding namespace must contain letters or digits")
        identity = f"{self.namespace}\0{self.model_id}\0{self.model_version}\0{self.dimension}"
        return f"{prefix}_chunks_{hashlib.sha256(identity.encode()).hexdigest()[:24]}"

    @property
    def projection_version(self) -> str:
        return f"{self.model_id}@{self.model_version}:d{self.dimension}"

    @classmethod
    def from_config(cls, namespace: str, path: Path) -> "EmbeddingSpec":
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
        embedding = config["embedding"]
        return cls(namespace, embedding["model_id"], embedding["digest"], embedding["dimension"])


def validate_vector(vector: list[float], dimension: int) -> None:
    if len(vector) != dimension or any(not math.isfinite(value) for value in vector):
        raise ValueError("embedding dimension mismatch or non-finite value")


@dataclass(frozen=True)
class VectorPoint:
    chunk_id: UUID
    document_id: UUID
    revision_id: UUID
    source: str
    source_id: str
    section: str
    language: str
    vector: list[float]


@dataclass(frozen=True)
class VectorHit:
    chunk_id: UUID
    document_id: UUID
    revision_id: UUID
    score: float


@dataclass(frozen=True)
class FeatureEmbeddingSpec:
    """Versioned Qdrant identity for feature-only shadow embeddings."""

    model_id: str
    model_digest: str
    dimension: int
    resolver_version: str

    def __post_init__(self) -> None:
        if not self.model_id or not self.model_digest or not self.resolver_version:
            raise ValueError("feature embedding identity is incomplete")
        if self.dimension < 1:
            raise ValueError("feature embedding dimension must be positive")

    @property
    def collection(self) -> str:
        identity = (
            f"{self.resolver_version}\0{self.model_id}\0{self.model_digest}\0{self.dimension}"
        )
        suffix = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
        version = re.sub(r"[^a-z0-9_]+", "_", self.resolver_version.lower()).strip("_")[:24]
        return f"graph_feature_mentions_{version}_{suffix}"

    @classmethod
    def from_config(cls, resolver_version: str, path: Path) -> "FeatureEmbeddingSpec":
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
        embedding = config["embedding"]
        return cls(
            model_id=embedding["model_id"],
            model_digest=embedding["digest"],
            dimension=embedding["dimension"],
            resolver_version=resolver_version,
        )


@dataclass(frozen=True)
class FeatureVectorPoint:
    normalized_feature_text: str
    raw_feature_text: str
    feature_key: str
    run_id: UUID
    document_count: int
    vector: list[float]

    @property
    def point_id(self) -> UUID:
        return uuid5(
            UUID("83c66fd2-3ae9-4b74-8f0e-0dbe0bbf9860"),
            f"{self.run_id}\0{self.feature_key}\0{self.normalized_feature_text}",
        )


@dataclass(frozen=True)
class FeatureVectorHit:
    normalized_feature_text: str
    raw_feature_text: str
    feature_key: str
    score: float


class QdrantIndex:
    def __init__(self, client: httpx.AsyncClient, spec: EmbeddingSpec) -> None:
        self.client = client
        self.spec = spec

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = await self.client.request(method, path, **kwargs)
        response.raise_for_status()
        body = response.json()
        if body.get("status") != "ok":
            raise RuntimeError("Qdrant operation failed")
        return body["result"]

    async def ensure_collection(self) -> None:
        path = f"/collections/{self.spec.collection}"
        response = await self.client.get(path)
        if response.status_code == 404:
            create = await self.client.put(
                path, json={"vectors": {"size": self.spec.dimension, "distance": "Cosine"}}
            )
            # Another worker may have created the same collection concurrently.
            if create.status_code not in (200, 201, 409):
                create.raise_for_status()
            response = await self.client.get(path)
        response.raise_for_status()
        body = response.json()
        if body.get("status") != "ok":
            raise RuntimeError("Qdrant collection lookup failed")
        vectors = body["result"]["config"]["params"]["vectors"]
        if vectors.get("size") != self.spec.dimension or vectors.get("distance") != "Cosine":
            raise ValueError("Qdrant collection vector configuration mismatch")

    async def upsert(self, points: list[VectorPoint]) -> None:
        if not points:
            return
        for point in points:
            validate_vector(point.vector, self.spec.dimension)
        result = await self._request(
            "PUT",
            f"/collections/{self.spec.collection}/points",
            params={"wait": "true"},
            json={
                "points": [
                    {
                        "id": str(point.chunk_id),
                        "vector": point.vector,
                        "payload": {
                            "document_id": str(point.document_id),
                            "revision_id": str(point.revision_id),
                            "chunk_id": str(point.chunk_id),
                            "source": point.source,
                            "source_id": point.source_id,
                            "section": point.section,
                            "language": point.language,
                        },
                    }
                    for point in points
                ]
            },
        )
        if result.get("status") != "completed":
            raise RuntimeError("Qdrant upsert was not completed")

    async def delete_revision(self, revision_id: UUID) -> None:
        result = await self._request(
            "POST",
            f"/collections/{self.spec.collection}/points/delete",
            params={"wait": "true"},
            json={
                "filter": {"must": [{"key": "revision_id", "match": {"value": str(revision_id)}}]}
            },
        )
        if result.get("status") != "completed":
            raise RuntimeError("Qdrant delete was not completed")

    async def count(self, *, revision_id: UUID | None = None) -> int:
        body: dict[str, Any] = {"exact": True}
        if revision_id is not None:
            body["filter"] = {
                "must": [{"key": "revision_id", "match": {"value": str(revision_id)}}]
            }
        result = await self._request(
            "POST", f"/collections/{self.spec.collection}/points/count", json=body
        )
        return int(result["count"])

    async def query(
        self,
        vector: list[float],
        *,
        limit: int,
        offset: int = 0,
        source: str | None = None,
        source_id: str | None = None,
        section: str | None = None,
        language: str | None = None,
        document_ids: list[UUID] | None = None,
    ) -> list[VectorHit]:
        validate_vector(vector, self.spec.dimension)
        if not 1 <= limit <= 100 or offset < 0:
            raise ValueError("invalid query window")
        must: list[dict[str, Any]] = []
        if source is not None:
            must.append({"key": "source", "match": {"value": source}})
        for key, value in (("source_id", source_id), ("section", section), ("language", language)):
            if value is not None:
                must.append({"key": key, "match": {"value": value}})
        if document_ids is not None:
            if not document_ids:
                return []
            must.append(
                {"key": "document_id", "match": {"any": [str(value) for value in document_ids]}}
            )
        body: dict[str, Any] = {
            "query": vector,
            "limit": limit,
            "offset": offset,
            "with_payload": True,
            "with_vector": False,
        }
        if must:
            body["filter"] = {"must": must}
        result = await self._request(
            "POST", f"/collections/{self.spec.collection}/points/query", json=body
        )
        return [
            VectorHit(
                chunk_id=UUID(item["payload"]["chunk_id"]),
                document_id=UUID(item["payload"]["document_id"]),
                revision_id=UUID(item["payload"]["revision_id"]),
                score=float(item["score"]),
            )
            for item in result["points"]
        ]


class FeatureEmbeddingIndex:
    """Qdrant adapter dedicated to feature mentions; never targets article chunks."""

    def __init__(self, client: httpx.AsyncClient, spec: FeatureEmbeddingSpec) -> None:
        self.client = client
        self.spec = spec

    async def ensure_collection(self) -> None:
        path = f"/collections/{self.spec.collection}"
        response = await self.client.get(path)
        if response.status_code == 404:
            create = await self.client.put(
                path, json={"vectors": {"size": self.spec.dimension, "distance": "Cosine"}}
            )
            if create.status_code not in (200, 201, 409):
                create.raise_for_status()
            response = await self.client.get(path)
        response.raise_for_status()
        body = response.json()
        vectors = body.get("result", {}).get("config", {}).get("params", {}).get("vectors", {})
        if (
            body.get("status") != "ok"
            or vectors.get("size") != self.spec.dimension
            or vectors.get("distance") != "Cosine"
        ):
            raise ValueError("feature shadow collection vector configuration mismatch")

    async def upsert(self, points: list[FeatureVectorPoint]) -> None:
        if not points:
            return
        ids: set[UUID] = set()
        qdrant_points = []
        for point in points:
            validate_vector(point.vector, self.spec.dimension)
            if point.point_id in ids:
                raise ValueError("duplicate deterministic feature point id")
            if point.document_count < 0:
                raise ValueError("feature document count cannot be negative")
            ids.add(point.point_id)
            qdrant_points.append(
                {
                    "id": str(point.point_id),
                    "vector": point.vector,
                    "payload": {
                        "raw_feature_text": point.raw_feature_text,
                        "normalized_feature_text": point.normalized_feature_text,
                        "feature_key": point.feature_key,
                        "resolver_version": self.spec.resolver_version,
                        "run_id": str(point.run_id),
                        "document_count": point.document_count,
                    },
                }
            )
        response = await self.client.put(
            f"/collections/{self.spec.collection}/points",
            params={"wait": "true"},
            json={"points": qdrant_points},
        )
        response.raise_for_status()
        body = response.json()
        if body.get("status") != "ok" or body.get("result", {}).get("status") != "completed":
            raise RuntimeError("feature shadow Qdrant upsert was not completed")

    async def query(
        self,
        vector: list[float],
        *,
        run_id: UUID,
        limit: int,
    ) -> list[FeatureVectorHit]:
        validate_vector(vector, self.spec.dimension)
        if not 1 <= limit <= 100:
            raise ValueError("feature candidate limit must be between 1 and 100")
        response = await self.client.post(
            f"/collections/{self.spec.collection}/points/query",
            json={
                "query": vector,
                "limit": limit,
                "with_payload": True,
                "with_vector": False,
                "filter": {
                    "must": [
                        {"key": "resolver_version", "match": {"value": self.spec.resolver_version}},
                        {"key": "run_id", "match": {"value": str(run_id)}},
                    ]
                },
            },
        )
        response.raise_for_status()
        body = response.json()
        if body.get("status") != "ok":
            raise RuntimeError("feature candidate query failed")
        return [
            FeatureVectorHit(
                normalized_feature_text=item["payload"]["normalized_feature_text"],
                raw_feature_text=item["payload"]["raw_feature_text"],
                feature_key=item["payload"]["feature_key"],
                score=float(item["score"]),
            )
            for item in body["result"]["points"]
        ]

    async def vectors(self, *, run_id: UUID) -> dict[str, list[float]]:
        offset: str | int | None = None
        result: dict[str, list[float]] = {}
        while True:
            body: dict[str, Any] = {
                "filter": {
                    "must": [
                        {"key": "resolver_version", "match": {"value": self.spec.resolver_version}},
                        {"key": "run_id", "match": {"value": str(run_id)}},
                    ]
                },
                "limit": 256,
                "with_payload": True,
                "with_vector": True,
            }
            if offset is not None:
                body["offset"] = offset
            response = await self.client.post(
                f"/collections/{self.spec.collection}/points/scroll", json=body
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("status") != "ok":
                raise RuntimeError("feature vector scroll failed")
            page = payload["result"]
            for point in page["points"]:
                vector = point.get("vector")
                if isinstance(vector, dict):
                    vector = vector.get("")
                if not isinstance(vector, list):
                    raise ValueError("feature shadow point has no vector")
                normalized = point["payload"]["normalized_feature_text"]
                validate_vector(vector, self.spec.dimension)
                result[normalized] = [float(value) for value in vector]
            offset = page.get("next_page_offset")
            if offset is None:
                return result
