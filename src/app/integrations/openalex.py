"""Клиент OpenAlex для ограниченного поиска и получения научных работ."""

import asyncio
import math
import os
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.domain.source import (
    FieldStatus,
    ScientificWork,
    SourceStatus,
    WorkAuthor,
    WorkResult,
    WorkTopic,
)

API_BASE = "https://api.openalex.org"
_WORK_ID = re.compile(r"W[0-9]+", re.IGNORECASE)
_AUTHOR_ID = re.compile(r"A[0-9]+", re.IGNORECASE)
_TOPIC_ID = re.compile(r"T[0-9]+", re.IGNORECASE)
_MAX_RESPONSE_BYTES = 10_000_000
_MAX_ABSTRACT_WORDS = 20_000


@dataclass(frozen=True)
class _Failure:
    code: str
    retry_after_seconds: float | None = None


def _string(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _external_id(value: Any, pattern: re.Pattern[str]) -> str | None:
    raw = _string(value)
    if raw is None:
        return None
    if raw.startswith("https://openalex.org/"):
        raw = raw.rsplit("/", 1)[-1]
    return raw.upper() if pattern.fullmatch(raw) else None


def _url(value: Any) -> str | None:
    raw = _string(value)
    if raw is None:
        return None
    try:
        parts = urlsplit(raw)
        return raw if parts.scheme == "https" and parts.netloc and not parts.username else None
    except ValueError:
        return None


def reconstruct_abstract(value: Any) -> str | None:
    """Восстановить abstract по позициям inverted index без заполнения пропусков."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("invalid abstract index")
    positions: dict[int, str] = {}
    for word, offsets in value.items():
        if not isinstance(word, str) or not isinstance(offsets, list):
            raise ValueError("invalid abstract index")
        for offset in offsets:
            if (
                isinstance(offset, bool)
                or not isinstance(offset, int)
                or offset < 0
                or offset >= _MAX_ABSTRACT_WORDS
                or offset in positions
            ):
                raise ValueError("invalid abstract position")
            positions[offset] = word
    if not positions:
        return None
    if len(positions) != max(positions) + 1:
        raise ValueError("abstract position gap")
    return " ".join(positions[index] for index in range(len(positions)))


def _date(value: Any) -> date | None:
    raw = _string(value)
    if raw is None:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _timestamp(value: Any) -> datetime | None:
    raw = _string(value)
    if raw is None:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def _field(value: Any) -> FieldStatus:
    return FieldStatus.MISSING if value is None else FieldStatus.AVAILABLE


def parse_work(value: Any) -> ScientificWork:
    """Нормализовать одну работу OpenAlex без загрузки полного текста."""
    if not isinstance(value, dict):
        raise ValueError("invalid work")
    work_id = _external_id(value.get("id"), _WORK_ID)
    if work_id is None:
        raise ValueError("missing work ID")
    raw_authors = value.get("authorships")
    raw_topics = value.get("topics")
    raw_references = value.get("referenced_works")
    if any(
        item is not None and not isinstance(item, list)
        for item in (raw_authors, raw_topics, raw_references)
    ):
        raise ValueError("invalid related records")
    authors: list[WorkAuthor] = []
    for authorship in raw_authors or []:
        if not isinstance(authorship, dict):
            continue
        author = authorship.get("author")
        if isinstance(author, dict):
            authors.append(
                WorkAuthor(
                    id=_external_id(author.get("id"), _AUTHOR_ID),
                    name=_string(author.get("display_name")),
                )
            )
    topics: list[WorkTopic] = []
    for item in raw_topics or []:
        if not isinstance(item, dict):
            continue
        raw_score = item.get("score")
        score = (
            float(raw_score)
            if isinstance(raw_score, int | float)
            and not isinstance(raw_score, bool)
            and math.isfinite(raw_score)
            else None
        )
        topics.append(
            WorkTopic(
                id=_external_id(item.get("id"), _TOPIC_ID),
                name=_string(item.get("display_name")),
                score=score,
            )
        )
    references = tuple(
        normalized
        for item in raw_references or []
        if (normalized := _external_id(item, _WORK_ID)) is not None
    )
    title = _string(value.get("title")) or _string(value.get("display_name"))
    abstract = reconstruct_abstract(value.get("abstract_inverted_index"))
    published = _date(value.get("publication_date"))
    updated = _timestamp(value.get("updated_date"))
    doi = _url(value.get("doi"))
    if doi and urlsplit(doi).hostname not in ("doi.org", "dx.doi.org"):
        doi = None
    primary = value.get("primary_location")
    landing_page = _url(primary.get("landing_page_url")) if isinstance(primary, dict) else None
    citations = value.get("cited_by_count")
    cited_by_count = (
        citations
        if isinstance(citations, int) and not isinstance(citations, bool) and citations >= 0
        else None
    )
    return ScientificWork(
        source="openalex",
        external_id=work_id,
        source_url=f"https://openalex.org/{work_id}",
        title=title,
        abstract=abstract,
        publication_date=published,
        updated_at=updated,
        doi=doi,
        landing_page_url=landing_page,
        language=_string(value.get("language")),
        authors=tuple(authors),
        topics=tuple(topics),
        referenced_work_ids=references,
        cited_by_count=cited_by_count,
        field_status={
            "title": _field(title),
            "abstract": _field(abstract),
            "publication_date": _field(published),
            "updated_at": _field(updated),
            "doi": _field(doi),
            "authors": _field(raw_authors),
            "topics": _field(raw_topics),
            "references": _field(raw_references),
            "citations": _field(cited_by_count),
        },
    )


class OpenAlexClient:
    """HTTP-адаптер с ограниченными повторами и явным cursor-контрактом."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        api_key: str | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
        max_attempts: int = 3,
    ) -> None:
        if max_attempts < 1 or max_attempts > 5:
            raise ValueError("max_attempts must be between 1 and 5")
        self.client = client
        self.api_key = api_key or None
        self.sleep = sleep
        self.clock = clock
        self.max_attempts = max_attempts
        self._not_before = 0.0
        self._blocked_until = 0.0
        self._remaining: int | None = None
        self._request_lock = asyncio.Lock()

    @classmethod
    def from_environment(cls, client: httpx.AsyncClient) -> "OpenAlexClient":
        """Взять необязательный API key из окружения."""
        return cls(client, api_key=os.getenv("OPENALEX_API_KEY"))

    @property
    def remaining_credits(self) -> int | None:
        return self._remaining

    @staticmethod
    def _retry_after(response: httpx.Response) -> float | None:
        raw = response.headers.get("Retry-After")
        try:
            return max(0.0, float(raw)) if raw is not None else None
        except ValueError:
            return None

    def _record_limits(self, response: httpx.Response) -> None:
        self._not_before = max(self._not_before, self.clock() + 0.05)
        remaining = response.headers.get("X-RateLimit-Remaining")
        reset = response.headers.get("X-RateLimit-Reset")
        if remaining and remaining.isdigit():
            self._remaining = int(remaining)
            if self._remaining == 0 and reset:
                try:
                    self._blocked_until = self.clock() + max(0.0, float(reset))
                except ValueError:
                    pass

    async def _get(
        self, path: str, *, params: dict[str, str] | None = None
    ) -> httpx.Response | _Failure:
        async with self._request_lock:
            if self.clock() < self._blocked_until:
                return _Failure("rate_limited", self._blocked_until - self.clock())
            for attempt in range(self.max_attempts):
                delay = self._not_before - self.clock()
                if delay > 0:
                    await self.sleep(delay)
                headers = {"Accept": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                try:
                    response = await self.client.get(
                        f"{API_BASE}{path}",
                        params=params,
                        headers=headers,
                        follow_redirects=False,
                        timeout=30.0,
                    )
                except httpx.RequestError:
                    if attempt + 1 == self.max_attempts:
                        return _Failure("network_error")
                    self._not_before = max(self._not_before, self.clock() + min(2**attempt, 8))
                    continue
                self._record_limits(response)
                if response.status_code == 429:
                    wait = self._retry_after(response) or min(2**attempt, 8)
                    self._not_before = max(self._not_before, self.clock() + wait)
                    if self.clock() < self._blocked_until or attempt + 1 == self.max_attempts:
                        return _Failure(
                            "rate_limited", max(wait, self._blocked_until - self.clock())
                        )
                    continue
                if 500 <= response.status_code < 600:
                    wait = min(2**attempt, 8)
                    self._not_before = max(self._not_before, self.clock() + wait)
                    if attempt + 1 == self.max_attempts:
                        return _Failure("server_error", wait)
                    continue
                if response.status_code in (200, 301, 404):
                    return response
                return _Failure("http_error")
            return _Failure("server_error")

    @staticmethod
    def _json(response: httpx.Response) -> Any:
        if len(response.content) > _MAX_RESPONSE_BYTES:
            raise ValueError("response too large")
        try:
            return response.json()
        except ValueError as exc:
            raise ValueError("invalid JSON") from exc

    async def search(
        self, query: str, *, per_page: int = 25, cursor: str = "*"
    ) -> WorkResult:
        if not query.strip() or len(query) > 2000:
            raise ValueError("query must contain 1-2000 characters")
        if per_page < 1 or per_page > 100:
            raise ValueError("per_page must be between 1 and 100")
        if not cursor or len(cursor) > 4096:
            raise ValueError("invalid cursor")
        response = await self._get(
            "/works",
            params={"search": query.strip(), "per_page": str(per_page), "cursor": cursor},
        )
        if isinstance(response, _Failure):
            return WorkResult(
                SourceStatus.UNAVAILABLE,
                error_code=response.code,
                retry_after_seconds=response.retry_after_seconds,
            )
        if response.status_code != 200:
            return WorkResult(SourceStatus.UNAVAILABLE, error_code="http_error")
        try:
            payload = self._json(response)
            if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
                raise ValueError("invalid search response")
            meta = payload.get("meta")
            if not isinstance(meta, dict):
                raise ValueError("missing metadata")
            works = tuple(parse_work(item) for item in payload["results"])
            next_cursor = meta.get("next_cursor")
            if next_cursor is not None and (
                not isinstance(next_cursor, str) or len(next_cursor) > 4096
            ):
                raise ValueError("invalid next cursor")
            count = meta.get("count")
            total = (
                count
                if isinstance(count, int) and not isinstance(count, bool) and count >= 0
                else None
            )
        except ValueError:
            return WorkResult(SourceStatus.UNAVAILABLE, error_code="invalid_response")
        return WorkResult(
            SourceStatus.OK if works else SourceStatus.EMPTY,
            works=works,
            next_cursor=next_cursor,
            total_count=total,
        )

    async def fetch(self, work_id: str) -> WorkResult:
        canonical = _external_id(work_id, _WORK_ID)
        if canonical is None:
            raise ValueError("invalid OpenAlex work ID")
        for _ in range(2):
            response = await self._get(f"/works/{canonical}")
            if isinstance(response, _Failure):
                return WorkResult(
                    SourceStatus.UNAVAILABLE,
                    error_code=response.code,
                    retry_after_seconds=response.retry_after_seconds,
                )
            if response.status_code == 404:
                return WorkResult(SourceStatus.EMPTY)
            if response.status_code == 301:
                location = response.headers.get("Location", "")
                parts = urlsplit(location)
                if parts.scheme != "https" or parts.netloc != "api.openalex.org":
                    return WorkResult(SourceStatus.UNAVAILABLE, error_code="unsafe_redirect")
                target = parts.path.removeprefix("/works/")
                replacement = _external_id(target, _WORK_ID)
                if not parts.path.startswith("/works/") or replacement is None:
                    return WorkResult(SourceStatus.UNAVAILABLE, error_code="unsafe_redirect")
                canonical = replacement
                continue
            try:
                work = parse_work(self._json(response))
            except ValueError:
                return WorkResult(SourceStatus.UNAVAILABLE, error_code="invalid_response")
            return WorkResult(SourceStatus.OK, works=(work,))
        return WorkResult(SourceStatus.UNAVAILABLE, error_code="redirect_loop")
