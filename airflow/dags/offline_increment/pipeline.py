"""Контракты ограниченного офлайн-инкремента без зависимости от Airflow."""

import hashlib
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial
from typing import Literal, Protocol, TypeVar

from app.services.ingestion import canonical_external_id

Source = Literal["epo_ops", "openalex"]
Backend = Literal["domain_graph", "qdrant"]
T = TypeVar("T")
LOGGER = logging.getLogger(__name__)
SAFE_ERRORS = frozenset(
    {
        "invalid_interval",
        "invalid_limits",
        "invalid_page",
        "invalid_cursor",
        "invalid_revision",
        "unsupported_source",
        "dependency_unavailable",
        "dependency_failure",
        "missing_ack",
        "quality_failed",
        "page_limit",
        "invalid_scope",
        "source_unavailable",
        "invalid_document",
        "revision_changed",
        "source_limit",
        "invalid_progress",
        "interval_page_limit",
    }
)


@dataclass(frozen=True)
class Interval:
    start: datetime
    end: datetime

    def validate(self, max_days: int) -> None:
        if (
            self.start.tzinfo is None
            or self.end.tzinfo is None
            or self.start.utcoffset() != timedelta(0)
            or self.end.utcoffset() != timedelta(0)
            or self.end <= self.start
            or self.end - self.start > timedelta(days=max_days)
        ):
            raise PipelineError("invalid_interval")


@dataclass(frozen=True)
class Limits:
    max_days: int = 31
    max_pages: int = 100
    max_interval_pages: int = 10000
    max_items_per_page: int = 100
    max_attempts: int = 3

    def validate(self) -> None:
        if not (
            1 <= self.max_days <= 366
            and 1 <= self.max_pages <= 10000
            and 1 <= self.max_interval_pages <= 10000
            and 1 <= self.max_items_per_page <= 100
            and 1 <= self.max_attempts <= 5
        ):
            raise PipelineError("invalid_limits")


@dataclass(frozen=True)
class Item:
    external_id: str
    revision_key: str


@dataclass(frozen=True)
class Page:
    items: tuple[Item, ...]
    next_cursor: str | None


@dataclass(frozen=True)
class Revision:
    revision_id: str
    content_hash: str
    # Включает существующие ревизии с незавершёнными заданиями после сбоя.
    needs_projection: bool


@dataclass(frozen=True)
class Progress:
    cursor: str | None
    completed: bool
    cursor_history: tuple[str, ...] = ()


class PipelineError(Exception):
    """Публичная ошибка содержит только фиксированный код, без данных источника."""


class RetryableError(Exception):
    """Сбой порта, который разрешено повторить в пределах бюджета."""


class Ports(Protocol):
    """Все методы должны быть идемпотентны; состояние и outbox — долговечны.

    freeze_page атомарно фиксирует первый результат discovery для cursor и возвращает
    уже сохранённый результат при повторе. commit_page атомарно проверяет версии ACK,
    QA и владение checkpoint, публикует поколение и продвигает checkpoint. Это порт
    для будущей интеграции, а не утверждение о возможностях текущего ingestion.
    """

    def progress(self, source: Source, interval: Interval) -> Progress: ...
    def frozen_page(
        self, source: Source, interval: Interval, cursor: str | None
    ) -> Page | None: ...
    def discover(
        self, source: Source, interval: Interval, cursor: str | None, limit: int
    ) -> Page: ...
    def freeze_page(
        self, source: Source, interval: Interval, cursor: str | None, page: Page
    ) -> Page: ...
    def ingest(self, source: Source, item: Item) -> Revision: ...
    def acknowledged(self, revision: Revision, backend: Backend) -> bool: ...
    def project(self, revision: Revision, backend: Backend) -> None: ...
    def quality(self, revision: Revision) -> bool: ...
    def commit_page(
        self,
        source: Source,
        interval: Interval,
        cursor: str | None,
        page: Page,
        revisions: tuple[Revision, ...],
        expected_history: tuple[str, ...],
    ) -> None: ...


def _call(operation: Callable[[], T], attempts: int) -> T:
    for attempt in range(attempts):
        try:
            return operation()
        except PipelineError as error:
            if str(error) in SAFE_ERRORS:
                raise PipelineError(str(error)) from None
            raise PipelineError("dependency_failure") from None
        except RetryableError:
            if attempt + 1 == attempts:
                raise PipelineError("dependency_unavailable") from None
        except Exception:
            raise PipelineError("dependency_failure") from None
    raise AssertionError("unreachable")


def run(ports: Ports, source: str, interval: Interval, limits: Limits) -> dict[str, int | str]:
    """Обработать сохранённые страницы; наружу вернуть лишь счётчики и статус."""
    if source not in ("epo_ops", "openalex"):
        raise PipelineError("unsupported_source")
    typed_source: Source = source  # type: ignore[assignment]
    limits.validate()
    interval.validate(limits.max_days)
    call = partial(_call, attempts=limits.max_attempts)
    state = call(partial(ports.progress, typed_source, interval))
    _validate_progress(state, limits)
    if state.completed:
        return {"stage": "complete", "pages": 0, "revisions": 0}
    cursor = state.cursor
    history = list(state.cursor_history)
    seen = set(history)
    pages = revisions_count = 0
    while pages < limits.max_pages:
        if len(seen) >= limits.max_interval_pages:
            raise PipelineError("interval_page_limit")
        current_hash = cursor_hash(cursor)
        if current_hash in seen:
            raise PipelineError("invalid_cursor")
        LOGGER.info("stage=discovery status=started")
        page = call(partial(ports.frozen_page, typed_source, interval, cursor))
        if page is None:
            page = call(
                partial(ports.discover, typed_source, interval, cursor, limits.max_items_per_page)
            )
            _validate_page(page, typed_source, limits, cursor)
            page = call(partial(ports.freeze_page, typed_source, interval, cursor, page))
        _validate_page(page, typed_source, limits, cursor)
        if page.next_cursor is not None and cursor_hash(page.next_cursor) in seen:
            raise PipelineError("invalid_cursor")
        revisions: list[Revision] = []
        for item in page.items:
            LOGGER.info("stage=ingestion status=started")
            revision = call(partial(ports.ingest, typed_source, item))
            if not revision.revision_id or not revision.content_hash:
                raise PipelineError("invalid_revision")
            if revision.needs_projection:
                LOGGER.info("stage=projection status=started")
                for backend in ("domain_graph", "qdrant"):
                    if not call(partial(ports.acknowledged, revision, backend)):
                        call(partial(ports.project, revision, backend))
                    if not call(partial(ports.acknowledged, revision, backend)):
                        raise PipelineError("missing_ack")
                LOGGER.info("stage=quality status=started")
                if not call(partial(ports.quality, revision)):
                    raise PipelineError("quality_failed")
                revisions.append(revision)
        LOGGER.info("stage=publish status=started")
        call(
            partial(
                ports.commit_page,
                typed_source,
                interval,
                cursor,
                page,
                tuple(revisions),
                tuple(history),
            )
        )
        LOGGER.info("stage=publish status=completed")
        seen.add(current_hash)
        history.append(current_hash)
        pages += 1
        revisions_count += len(revisions)
        if page.next_cursor is None:
            return {"stage": "complete", "pages": pages, "revisions": revisions_count}
        cursor = page.next_cursor
    raise PipelineError("page_limit")


def _validate_page(page: Page, source: Source, limits: Limits, cursor: str | None) -> None:
    if (
        not isinstance(page, Page)
        or not isinstance(page.items, tuple)
        or len(page.items) > limits.max_items_per_page
        or (not page.items and page.next_cursor is not None)
        or (
            page.next_cursor is not None
            and (
                not isinstance(page.next_cursor, str)
                or not page.next_cursor
                or len(page.next_cursor) > 1024
                or page.next_cursor == cursor
            )
        )
    ):
        raise PipelineError("invalid_page")
    identifiers: set[str] = set()
    for item in page.items:
        if (
            not isinstance(item, Item)
            or not isinstance(item.external_id, str)
            or len(item.external_id) > 128
            or not isinstance(item.revision_key, str)
            or not item.revision_key
            or len(item.revision_key) > 256
        ):
            raise PipelineError("invalid_page")
        try:
            identifier = canonical_external_id(source, item.external_id)
        except ValueError:
            raise PipelineError("invalid_page") from None
        if identifier in identifiers:
            raise PipelineError("invalid_page")
        identifiers.add(identifier)


def cursor_hash(cursor: str | None) -> str:
    """Хеш позиции отличает начало интервала от курсора источника."""
    value = b"\x00" if cursor is None else b"\x01" + cursor.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _validate_progress(state: Progress, limits: Limits) -> None:
    if (
        not isinstance(state, Progress)
        or not isinstance(state.completed, bool)
        or not isinstance(state.cursor_history, tuple)
        or len(state.cursor_history) > limits.max_interval_pages
        or any(
            not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None
            for value in state.cursor_history
        )
        or len(set(state.cursor_history)) != len(state.cursor_history)
        or (
            state.cursor is not None
            and (not isinstance(state.cursor, str) or not state.cursor or len(state.cursor) > 1024)
        )
        or (state.cursor is not None and not state.cursor_history)
        or (state.cursor is None and state.cursor_history and not state.completed)
        or (state.cursor_history and state.cursor_history[0] != cursor_hash(None))
        or (state.completed and (state.cursor is not None or not state.cursor_history))
    ):
        raise PipelineError("invalid_progress")
