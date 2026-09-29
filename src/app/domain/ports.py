"""Общие интерфейсы сервисов и адаптеров для инверсии зависимостей."""

from typing import Protocol

from app.domain.inference import InferenceProvider as InferenceProvider


class AsyncHealthCheck(Protocol):
    async def check(self) -> bool: ...


class RunRepository(Protocol):
    async def get_run(self, run_id: str, *, owner_id: str) -> object | None: ...
