"""Кэш стадий с обязательной проверкой области доступа вызывающей стороной."""

import hashlib
import hmac
from collections.abc import Callable
from typing import Any, Literal, TypeVar
from uuid import UUID

from app.integrations.redis_cache import RedisCache

T = TypeVar("T")
Stage = Literal["retrieval", "rerank", "graph"]


class ScopedStageCache:
    def __init__(self, cache: RedisCache) -> None:
        self.cache = cache

    def _chat_scope(self, conversation_id: UUID) -> str:
        digest = hmac.new(
            self.cache.scope_secret, b"chat:" + conversation_id.bytes, hashlib.sha256
        ).hexdigest()
        return f"c1_{digest}"

    def key(
        self,
        stage: Stage,
        owner_id: UUID,
        conversation_id: UUID,
        *,
        version: Any,
        models: Any,
        params: Any,
        inputs: Any,
    ) -> str:
        if stage not in {"retrieval", "rerank", "graph"}:
            raise ValueError("unsupported cache stage")
        if any(value is None for value in (version, models, params, inputs)):
            raise ValueError("cache dimensions must be explicit")
        return ":".join(
            (
                "stage:v3",
                stage,
                self.cache.tenant_scope(owner_id),
                self._chat_scope(conversation_id),
                self.cache._hash(
                    {"version": version, "models": models, "params": params, "inputs": inputs}
                ),
            )
        )

    def get_or_compute(
        self,
        stage: Stage,
        owner_id: UUID,
        conversation_id: UUID,
        *,
        version: Any,
        models: Any,
        params: Any,
        inputs: Any,
        authorize: Callable[[], None],
        validate: Callable[[Any], T],
        compute: Callable[[], T],
    ) -> T:
        # Проверка должна обращаться к PostgreSQL, а для graph — также к run.
        authorize()
        key = self.key(
            stage,
            owner_id,
            conversation_id,
            version=version,
            models=models,
            params=params,
            inputs=inputs,
        )
        cached = self.cache.get_json(key)
        if cached is not None:
            try:
                result = validate(cached)
            except (TypeError, ValueError, KeyError):
                pass
            else:
                authorize()
                return result
        result = compute()
        authorize()
        self.cache.set_json(key, result, layer=stage)
        return result

    def invalidate_conversation(self, owner_id: UUID, conversation_id: UUID) -> bool:
        if self.cache.client is None:
            return True
        try:
            scan_iter = getattr(self.cache.client, "scan_iter", None)
            if scan_iter is None:
                return False
            pattern = (
                f"stage:v3:*:{self.cache.tenant_scope(owner_id)}:"
                f"{self._chat_scope(conversation_id)}:*"
            )
            keys = list(scan_iter(match=pattern))
            if keys:
                self.cache.client.delete(*keys)
            return True
        except Exception:
            return False
