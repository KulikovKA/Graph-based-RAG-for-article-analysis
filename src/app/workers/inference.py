"""Общий слот генерации с ограниченной очередью и подтверждённой остановкой."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from app.domain.inference import (
    InferenceCancelled,
    InferenceTimeout,
    InferenceUnavailable,
)

T = TypeVar("T")


class GenerationGate:
    def __init__(self, *, waiting_capacity: int = 8, stop_grace: float = 5.0) -> None:
        if waiting_capacity < 0 or stop_grace <= 0:
            raise ValueError("invalid generation gate configuration")
        self._queue = asyncio.Semaphore(waiting_capacity + 1)
        self._slot = asyncio.Lock()
        self._stop_grace = stop_grace
        self._poisoned = False

    @property
    def blocked(self) -> bool:
        return self._poisoned

    def quarantine(self) -> None:
        self._poisoned = True

    def recover(self) -> None:
        """Вызывать после внешней проверки остановки backend-запроса."""
        if self._slot.locked():
            raise InferenceUnavailable("generation slot is still occupied")
        self._poisoned = False

    async def run(
        self, operation: Callable[[], Awaitable[T]], *, timeout: float,
        cancel: asyncio.Event | None = None,
        heartbeat: Callable[[], Awaitable[None]] | None = None,
    ) -> T:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if self._poisoned:
            raise InferenceUnavailable("generation backend requires recovery")
        deadline = time.monotonic() + timeout
        if self._queue.locked():
            raise InferenceUnavailable("generation queue is full")
        await self._queue.acquire()
        acquired = False
        work: asyncio.Future[T] | None = None
        heartbeat_task: asyncio.Task[None] | None = None
        try:
            await self._acquire_slot(deadline, cancel)
            acquired = True
            if self._poisoned:
                raise InferenceUnavailable("generation backend requires recovery")
            if heartbeat is not None:
                heartbeat_task = asyncio.create_task(self._beat(heartbeat))
            work = asyncio.ensure_future(operation())
            return await self._await_or_cancel(work, deadline, cancel)
        except (InferenceTimeout, InferenceCancelled, asyncio.CancelledError):
            if work is not None and not work.done():
                work.cancel()
                try:
                    await asyncio.wait_for(asyncio.shield(work), self._stop_grace)
                except asyncio.CancelledError:
                    # Backend-задача подтвердила отмену.
                    if not work.done():
                        self._poisoned = True
                except TimeoutError:
                    self._poisoned = True
                except Exception:
                    self._poisoned = True
            raise
        finally:
            if heartbeat_task is not None:
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass
            if acquired:
                self._slot.release()
            self._queue.release()

    async def _beat(self, heartbeat: Callable[[], Awaitable[None]]) -> None:
        while True:
            await heartbeat()
            await asyncio.sleep(1)

    async def _acquire_slot(self, deadline: float, cancel: asyncio.Event | None) -> None:
        waiter = asyncio.create_task(self._slot.acquire())
        try:
            await self._await_or_cancel(waiter, deadline, cancel)
        except BaseException:
            if waiter.done() and not waiter.cancelled() and waiter.result():
                self._slot.release()
            else:
                waiter.cancel()
            raise

    async def _await_or_cancel(
        self, awaitable: Awaitable[T], deadline: float, cancel: asyncio.Event | None,
    ) -> T:
        task = asyncio.ensure_future(awaitable)
        cancel_task = asyncio.create_task(cancel.wait()) if cancel is not None else None
        try:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise InferenceTimeout("inference deadline exceeded")
            pending_set: set[asyncio.Future[Any]] = {task}
            if cancel_task is not None:
                pending_set.add(cancel_task)
            done, _ = await asyncio.wait(pending_set, timeout=remaining,
                                         return_when=asyncio.FIRST_COMPLETED)
            if cancel_task is not None and cancel_task in done:
                raise InferenceCancelled("inference cancelled")
            if task not in done:
                raise InferenceTimeout("inference deadline exceeded")
            return task.result()
        finally:
            if cancel_task is not None:
                cancel_task.cancel()
            # Вызывающий код подтверждает остановку операции до освобождения слота.
            if task is not awaitable and not task.done():
                task.cancel()
