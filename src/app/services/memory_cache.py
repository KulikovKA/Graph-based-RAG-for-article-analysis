"""Кэш стадий с обязательной проверкой области доступа вызывающей стороной."""

import hashlib
import hmac
import json
import logging
from collections.abc import Awaitable, Callable, Iterator
from contextlib import AbstractContextManager, contextmanager, nullcontext
from typing import Any, Literal, TypeVar, cast
from uuid import UUID

from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.integrations.redis_cache import RedisCache, RedisClient
from app.storage.models import Conversation

T = TypeVar("T")
Stage = Literal["retrieval", "rerank", "graph"]
logger = logging.getLogger(__name__)


def build_stage_cache(redis_url: str | None, scope_secret: str | None) -> "ScopedStageCache | None":
    if not redis_url or not scope_secret:
        return None
    secret = hashlib.sha256(b"article-stage-cache-v2\x00" + scope_secret.encode()).digest()
    client = Redis.from_url(redis_url, socket_connect_timeout=0.25, socket_timeout=0.25)
    return ScopedStageCache(RedisCache(cast(RedisClient, client), scope_secret=secret))


@contextmanager
def conversation_write_guard(
    sessions: sessionmaker[Session],
    owner_id: UUID,
    conversation_id: UUID,
    *,
    missing_error: Callable[[], Exception] = lambda: LookupError("conversation not found"),
) -> Iterator[None]:
    with sessions.begin() as session:
        row = session.scalar(
            select(Conversation)
            .where(Conversation.id == conversation_id, Conversation.owner_user_id == owner_id)
            .with_for_update()
        )
        if row is None:
            raise missing_error()
        yield


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
                hmac.new(
                    self.cache.scope_secret,
                    json.dumps(
                        {"version": version, "models": models, "params": params, "inputs": inputs},
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode(),
                    hashlib.sha256,
                ).hexdigest(),
            )
        )

    def _epoch_key(self, owner_id: UUID, conversation_id: UUID) -> str:
        return (
            f"stage-epoch:v1:{self.cache.tenant_scope(owner_id)}:"
            f"{self._chat_scope(conversation_id)}"
        )

    def _epoch(self, owner_id: UUID, conversation_id: UUID) -> str | None:
        try:
            if self.cache.client is None:
                return None
            value = self.cache.client.get(self._epoch_key(owner_id, conversation_id))
            return value.decode() if isinstance(value, bytes) else str(value or "0")
        except Exception:
            return None

    def _read(self, key: str, epoch: str | None) -> tuple[Any, str]:
        if epoch is None or self.cache.client is None:
            return None, "unavailable"
        try:
            raw = self.cache.client.get(key)
            if raw is None:
                return None, "miss"
            envelope = json.loads(raw)
            payload = envelope["payload"]
            body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            signature = hmac.new(
                self.cache.scope_secret, (key + "\x00" + body).encode(), hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, envelope["signature"]):
                return None, "miss"
            return payload, "miss"
        except (ValueError, TypeError, UnicodeError, KeyError):
            return None, "miss"
        except Exception:
            return None, "unavailable"

    def _write(self, key: str, epoch_key: str, epoch: str | None, value: Any, stage: Stage) -> None:
        if epoch is None or self.cache.client is None:
            return
        try:
            body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            signature = hmac.new(
                self.cache.scope_secret, (key + "\x00" + body).encode(), hashlib.sha256
            ).hexdigest()
            payload = json.dumps(
                {"payload": value, "signature": signature},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            self.cache.client.eval(
                "if (redis.call('GET', KEYS[1]) or '0') == ARGV[1] then "
                "return redis.call('SET', KEYS[2], ARGV[2], 'EX', ARGV[3]) end return false",
                2,
                epoch_key,
                key,
                epoch,
                payload,
                self.cache.TTL_SECONDS[stage],
            )
        except Exception:
            pass

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
        write_guard: Callable[[], AbstractContextManager[None]] = nullcontext,
    ) -> T:
        authorize()
        epoch = self._epoch(owner_id, conversation_id)
        key = (
            self.key(
                stage,
                owner_id,
                conversation_id,
                version=version,
                models=models,
                params=params,
                inputs=inputs,
            )
            + ":"
            + str(epoch)
        )
        cached, outcome = self._read(key, epoch)
        if cached is not None:
            try:
                result = validate(cached)
            except (TypeError, ValueError, KeyError):
                pass
            else:
                authorize()
                logger.info("stage_cache stage=%s outcome=hit", stage)
                return result
        logger.info("stage_cache stage=%s outcome=%s", stage, outcome)
        result = compute()
        authorize()
        with write_guard():
            self._write(key, self._epoch_key(owner_id, conversation_id), epoch, result, stage)
        return result

    async def get_or_compute_async(
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
        compute: Callable[[], Awaitable[T]],
        should_cache: Callable[[T], bool] = lambda _: True,
        write_guard: Callable[[], AbstractContextManager[None]] = nullcontext,
    ) -> T:
        authorize()
        epoch = self._epoch(owner_id, conversation_id)
        key = (
            self.key(
                stage,
                owner_id,
                conversation_id,
                version=version,
                models=models,
                params=params,
                inputs=inputs,
            )
            + ":"
            + str(epoch)
        )
        cached, outcome = self._read(key, epoch)
        if cached is not None:
            try:
                result = validate(cached)
            except (TypeError, ValueError, KeyError):
                pass
            else:
                authorize()
                logger.info("stage_cache stage=%s outcome=hit", stage)
                return result
        logger.info("stage_cache stage=%s outcome=%s", stage, outcome)
        result = await compute()
        authorize()
        if should_cache(result):
            with write_guard():
                self._write(key, self._epoch_key(owner_id, conversation_id), epoch, result, stage)
        return result

    def invalidate_conversation(self, owner_id: UUID, conversation_id: UUID) -> bool:
        if self.cache.client is None:
            return True
        try:
            epoch_key = self._epoch_key(owner_id, conversation_id)
            self.cache.client.incr(epoch_key)
            self.cache.client.expire(epoch_key, 2 * 86400)
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
