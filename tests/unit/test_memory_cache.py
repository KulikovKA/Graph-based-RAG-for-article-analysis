from uuid import uuid4

from app.integrations.redis_cache import RedisCache


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get(self, name: str) -> str | None:
        return self.values.get(name)

    def set(self, name: str, value: str, *, ex: int) -> None:
        self.values[name] = value

    def delete(self, *names: str) -> int:
        for name in names:
            self.values.pop(name, None)
        return len(names)

    def scan_iter(self, *, match: str):
        scope = match.removeprefix("*:").removesuffix(":*")
        return (key for key in self.values if f":{scope}:" in key)


def test_cache_keys_scope_user_and_all_query_dimensions() -> None:
    cache = RedisCache(FakeRedis(), scope_secret=b"s" * 32)
    user_a, user_b, generation = uuid4(), uuid4(), uuid4()
    kwargs = {
        "query": {"text": "same", "constraints": []},
        "idea": {"features": ["x"]},
        "generation_id": generation,
        "retrieval_config": {"top_k": 10},
    }
    key_a = cache.retrieval_key(user_a, **kwargs)
    assert key_a != cache.retrieval_key(user_b, **kwargs)
    assert key_a != cache.retrieval_key(user_a, **{**kwargs, "query": {"text": "different"}})
    assert key_a != cache.retrieval_key(user_a, **{**kwargs, "generation_id": uuid4()})
    assert key_a != cache.retrieval_key(
        user_a, **{**kwargs, "retrieval_config": {"top_k": 20}}
    )


def test_cache_roundtrip_failure_fallback_and_tenant_invalidation() -> None:
    client = FakeRedis()
    cache = RedisCache(client, scope_secret=b"s" * 32)
    user = uuid4()
    key = cache.retrieval_key(
        user,
        query="q",
        idea={},
        generation_id=uuid4(),
        retrieval_config={},
    )
    assert cache.set_json(key, {"candidate_refs": ["doc:rev"]}, layer="retrieval")
    assert cache.get_json(key) == {"candidate_refs": ["doc:rev"]}
    assert cache.invalidate_tenant(user)
    assert cache.get_json(key) is None

    class BrokenRedis(FakeRedis):
        def get(self, name: str) -> str | None:
            raise ConnectionError("offline")

        def set(self, name: str, value: str, *, ex: int) -> None:
            raise ConnectionError("offline")

    fallback = RedisCache(BrokenRedis(), scope_secret=b"s" * 32)
    assert fallback.get_json("key") is None
    assert not fallback.set_json("key", {}, layer="retrieval")
    assert RedisCache(None, scope_secret=b"s" * 32).get_json("key") is None
