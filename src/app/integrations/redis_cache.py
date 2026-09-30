"""Tenant-scoped, versioned cache keys with transparent Redis failure fallback.

The client is injected so the PostgreSQL-backed application remains usable when
Redis is unavailable or deliberately not configured.
"""

import hashlib
import hmac
import json
from typing import Any, Protocol
from uuid import UUID


class RedisClient(Protocol):
    def get(self, name: str) -> bytes | str | None: ...

    def set(self, name: str, value: str, *, ex: int) -> Any: ...

    def delete(self, *names: str) -> Any: ...


class RedisCache:
    """Small JSON cache; Redis exceptions become misses and skipped writes."""

    TTL_SECONDS = {
        "public_metadata": 24 * 60 * 60,
        "retrieval": 30 * 60,
        "rerank": 24 * 60 * 60,
        "graph": 10 * 60,
    }

    def __init__(self, client: RedisClient | None, *, scope_secret: bytes) -> None:
        if len(scope_secret) < 32:
            raise ValueError("scope_secret must contain at least 32 bytes")
        self.client = client
        self.scope_secret = scope_secret

    def tenant_scope(self, user_id: UUID, *, key_version: str = "k1") -> str:
        digest = hmac.new(self.scope_secret, user_id.bytes, hashlib.sha256).hexdigest()
        return f"{key_version}_{digest}"

    @staticmethod
    def _hash(value: Any) -> str:
        canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def retrieval_key(
        self,
        user_id: UUID,
        *,
        query: Any,
        idea: Any,
        generation_id: UUID,
        retrieval_config: Any,
    ) -> str:
        return ":".join(
            (
                "retr:v2",
                self.tenant_scope(user_id),
                self._hash(query),
                self._hash(idea),
                str(generation_id),
                self._hash(retrieval_config),
            )
        )

    def rerank_key(
        self,
        user_id: UUID,
        *,
        query: Any,
        candidates: Any,
        model_version: str,
        rerank_config: Any,
    ) -> str:
        return ":".join(
            (
                "rerank:v2",
                self.tenant_scope(user_id),
                self._hash(query),
                self._hash(candidates),
                model_version,
                self._hash(rerank_config),
            )
        )

    def graph_key(
        self,
        user_id: UUID,
        *,
        run_id: UUID,
        graph_version: str,
        node_id: str,
        cursor: Any,
        filter_limits: Any,
    ) -> str:
        return ":".join(
            (
                "graph:v2",
                self.tenant_scope(user_id),
                str(run_id),
                graph_version,
                self._hash(node_id),
                self._hash(cursor),
                self._hash(filter_limits),
            )
        )

    def get_json(self, key: str) -> Any | None:
        if self.client is None:
            return None
        try:
            value = self.client.get(key)
            if value is None:
                return None
            if isinstance(value, bytes):
                value = value.decode("utf-8")
            return json.loads(value)
        except Exception:  # Cache errors must not turn a durable operation into a failure.
            return None

    def set_json(self, key: str, value: Any, *, layer: str) -> bool:
        if layer not in self.TTL_SECONDS:
            raise ValueError("unsupported cache layer")
        if self.client is None:
            return False
        try:
            payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            self.client.set(key, payload, ex=self.TTL_SECONDS[layer])
            return True
        except Exception:
            return False

    def invalidate_tenant(self, user_id: UUID) -> bool:
        """Invalidate key scopes at account removal; a failed delete is reported."""
        if self.client is None:
            return True
        try:
            # Redis SCAN is intentionally delegated to the client when available.
            scan_iter = getattr(self.client, "scan_iter", None)
            if scan_iter is None:
                return False
            keys = list(scan_iter(match=f"*:{self.tenant_scope(user_id)}:*"))
            if keys:
                self.client.delete(*keys)
            return True
        except Exception:
            return False
