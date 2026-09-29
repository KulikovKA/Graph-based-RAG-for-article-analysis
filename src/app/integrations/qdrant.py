"""Small Qdrant REST adapter for the product's revision-scoped vector projection."""

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx


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
            json={"points": [
                {"id": str(point.chunk_id), "vector": point.vector, "payload": {
                    "document_id": str(point.document_id),
                    "revision_id": str(point.revision_id),
                    "chunk_id": str(point.chunk_id),
                    "source": point.source,
                    "source_id": point.source_id,
                    "section": point.section,
                    "language": point.language,
                }} for point in points
            ]},
        )
        if result.get("status") != "completed":
            raise RuntimeError("Qdrant upsert was not completed")

    async def delete_revision(self, revision_id: UUID) -> None:
        result = await self._request(
            "POST",
            f"/collections/{self.spec.collection}/points/delete",
            params={"wait": "true"},
            json={"filter": {"must": [{"key": "revision_id", "match": {
                "value": str(revision_id)
            }}]}},
        )
        if result.get("status") != "completed":
            raise RuntimeError("Qdrant delete was not completed")

    async def count(self, *, revision_id: UUID | None = None) -> int:
        body: dict[str, Any] = {"exact": True}
        if revision_id is not None:
            body["filter"] = {"must": [{"key": "revision_id", "match": {
                "value": str(revision_id)
            }}]}
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
        for key, value in (("source_id", source_id), ("section", section),
                           ("language", language)):
            if value is not None:
                must.append({"key": key, "match": {"value": value}})
        if document_ids is not None:
            if not document_ids:
                return []
            must.append({"key": "document_id", "match": {
                "any": [str(value) for value in document_ids]
            }})
        body: dict[str, Any] = {
            "query": vector, "limit": limit, "offset": offset,
            "with_payload": True, "with_vector": False,
        }
        if must:
            body["filter"] = {"must": must}
        result = await self._request(
            "POST", f"/collections/{self.spec.collection}/points/query", json=body
        )
        return [VectorHit(
            chunk_id=UUID(item["payload"]["chunk_id"]),
            document_id=UUID(item["payload"]["document_id"]),
            revision_id=UUID(item["payload"]["revision_id"]),
            score=float(item["score"]),
        ) for item in result["points"]]
