"""Dependency inversion ports shared by services and adapters."""

from typing import Protocol


class AsyncHealthCheck(Protocol):
    async def check(self) -> bool: ...


class RunRepository(Protocol):
    async def get_run(self, run_id: str, *, owner_id: str) -> object | None: ...


class InferenceProvider(Protocol):
    async def complete_json(self, *, model_id: str, prompt_version: str, request_id: str,
                            timeout: float, prompt: str) -> object: ...

    async def stream_text(self, *, model_id: str, prompt_version: str, request_id: str,
                          timeout: float, prompt: str) -> object: ...

    async def embed(self, *, model_id: str, request_id: str,
                    texts: list[str]) -> list[list[float]]: ...

    async def rerank(self, *, model_id: str, request_id: str, query: str,
                     documents: list[str]) -> list[float]: ...
