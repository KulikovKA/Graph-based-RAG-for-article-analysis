"""Проверки адаптера OpenAlex на локальных ответах API."""

import asyncio
import json
from pathlib import Path

import httpx

from app.domain.source import FieldStatus, SourceStatus
from app.integrations.openalex import OpenAlexClient, parse_work, reconstruct_abstract

FIXTURES = Path(__file__).parents[1] / "fixtures" / "openalex"


def fixture(name: str) -> dict:  # type: ignore[type-arg]
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))  # type: ignore[no-any-return]


class FakeTime:
    def __init__(self) -> None:
        self.now = 0.0
        self.waits: list[float] = []

    def clock(self) -> float:
        return self.now

    async def sleep(self, duration: float) -> None:
        self.waits.append(duration)
        self.now += duration


def test_normalization_and_nullable_fields() -> None:
    rich = parse_work(fixture("work_with_abstract.json"))
    assert rich.external_id == "W1234567890"
    assert rich.source_url == "https://openalex.org/W1234567890"
    assert rich.abstract == "Graph retrieval supports research."
    assert rich.publication_date is not None
    assert rich.publication_date.isoformat() == "2024-04-12"
    assert rich.updated_at is not None
    assert rich.updated_at.isoformat() == "2025-02-03T04:05:06+00:00"
    assert rich.doi == "https://doi.org/10.1234/example"
    assert rich.landing_page_url == "https://journal.example/article/1"
    assert [(author.id, author.name) for author in rich.authors] == [
        ("A123", "Ada Researcher"),
        ("A456", "Boris Scientist"),
    ]
    assert [(topic.id, topic.name, topic.score) for topic in rich.topics] == [
        ("T123", "Information retrieval", 0.87)
    ]
    assert rich.referenced_work_ids == ("W9876543210",)
    assert rich.cited_by_count == 17
    assert rich.field_status["abstract"] == FieldStatus.AVAILABLE

    sparse = parse_work(fixture("work_without_abstract.json"))
    assert sparse.title == "Sparse record"
    assert sparse.abstract is None
    assert sparse.publication_date is None
    assert sparse.updated_at is None
    assert sparse.doi is None
    assert sparse.authors == () and sparse.topics == ()
    assert sparse.referenced_work_ids == ()
    assert sparse.cited_by_count is None
    assert sparse.field_status["abstract"] == FieldStatus.MISSING
    assert sparse.field_status["authors"] == FieldStatus.AVAILABLE
    assert sparse.field_status["topics"] == FieldStatus.MISSING


def test_abstract_index_rejects_gaps() -> None:
    assert reconstruct_abstract(None) is None
    try:
        reconstruct_abstract({"one": [0], "three": [2]})
    except ValueError:
        pass
    else:
        raise AssertionError("Пропуск позиции abstract должен быть ошибкой")


def test_search_cursor_and_repeat_fetch_are_idempotent() -> None:
    clock = FakeTime()
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.openalex.org"
        assert request.headers["Authorization"] == "Bearer example-key"
        calls.append(str(request.url))
        if request.url.path == "/works":
            assert request.url.params["search"] == "graph retrieval"
            assert request.url.params["per_page"] == "1"
            cursor = request.url.params["cursor"]
            if cursor == "*":
                assert request.url.params["filter"] == "from_publication_date:2024-01-01"
                return httpx.Response(
                    200,
                    json={
                        "meta": {"count": 2, "next_cursor": "cursor-two"},
                        "results": [fixture("work_with_abstract.json")],
                    },
                    headers={"X-RateLimit-Remaining": "40"},
                )
            assert cursor == "cursor-two"
            return httpx.Response(
                200,
                json={
                    "meta": {"count": 2, "next_cursor": None},
                    "results": [fixture("work_without_abstract.json")],
                },
            )
        assert request.url.path == "/works/W1234567890"
        return httpx.Response(200, json=fixture("work_with_abstract.json"))

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            adapter = OpenAlexClient(
                http, api_key="example-key", clock=clock.clock, sleep=clock.sleep
            )
            first = await adapter.search(
                "graph retrieval",
                per_page=1,
                filters="from_publication_date:2024-01-01",
            )
            assert first.status == SourceStatus.OK
            assert first.total_count == 2
            assert first.next_cursor == "cursor-two"
            assert [work.external_id for work in first.works] == ["W1234567890"]
            assert adapter.remaining_credits == 40
            second = await adapter.search("graph retrieval", per_page=1, cursor=first.next_cursor)
            assert second.status == SourceStatus.OK
            assert second.next_cursor is None
            assert [work.external_id for work in second.works] == ["W5555555555"]
            fetched_once = await adapter.fetch("W1234567890")
            fetched_twice = await adapter.fetch("https://openalex.org/W1234567890")
            assert fetched_once == fetched_twice
            assert fetched_once.works == first.works

    asyncio.run(scenario())
    assert len(calls) == 4
    assert len(clock.waits) == 3


def test_rate_limit_retry_and_budget_block() -> None:
    clock = FakeTime()
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        assert "Authorization" not in request.headers
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "2"})
        return httpx.Response(
            200,
            json=fixture("work_with_abstract.json"),
            headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "30"},
        )

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            adapter = OpenAlexClient(http, clock=clock.clock, sleep=clock.sleep)
            result = await adapter.fetch("W1234567890")
            assert result.status == SourceStatus.OK
            assert clock.waits == [2.0]
            assert adapter.remaining_credits == 0
            blocked = await adapter.fetch("W1234567890")
            assert blocked.status == SourceStatus.UNAVAILABLE
            assert blocked.error_code == "rate_limited"
            assert blocked.retry_after_seconds is not None
            assert blocked.retry_after_seconds >= 29

    asyncio.run(scenario())
    assert calls == 2


def test_server_errors_stop_after_bounded_retries() -> None:
    clock = FakeTime()
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503)

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            adapter = OpenAlexClient(http, clock=clock.clock, sleep=clock.sleep)
            result = await adapter.fetch("W1234567890")
            assert result.status == SourceStatus.UNAVAILABLE
            assert result.error_code == "server_error"
            assert result.retry_after_seconds == 4

    asyncio.run(scenario())
    assert calls == 3
    assert clock.waits == [1.0, 2.0]


def test_rate_limit_stops_after_bounded_retries() -> None:
    clock = FakeTime()
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(429, headers={"Retry-After": "3"})

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            adapter = OpenAlexClient(http, clock=clock.clock, sleep=clock.sleep)
            result = await adapter.fetch("W1234567890")
            assert result.status == SourceStatus.UNAVAILABLE
            assert result.error_code == "rate_limited"
            assert result.retry_after_seconds == 3

    asyncio.run(scenario())
    assert calls == 3
    assert clock.waits == [3.0, 3.0]


def test_missing_work_and_redirect_validation() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/works/W1":
            return httpx.Response(404)
        if request.url.path == "/works/W2":
            return httpx.Response(301, headers={"Location": "https://elsewhere.example/works/W3"})
        if request.url.path == "/works/W3":
            return httpx.Response(301, headers={"Location": "https://api.openalex.org/works/W1234567890"})
        return httpx.Response(200, json=fixture("work_with_abstract.json"))

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            adapter = OpenAlexClient(http, sleep=FakeTime().sleep)
            assert (await adapter.fetch("W1")).status == SourceStatus.EMPTY
            assert (await adapter.fetch("W2")).error_code == "unsafe_redirect"
            merged = await adapter.fetch("W3")
            assert merged.status == SourceStatus.OK
            assert merged.works[0].external_id == "W1234567890"

    asyncio.run(scenario())
