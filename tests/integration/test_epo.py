"""Проверки EPO OPS на синтетических XML-ответах без обращения к внешнему сервису."""

import asyncio
import logging
from pathlib import Path

import httpx

from app.domain.source import FieldStatus, SourceStatus
from app.integrations.epo import EpoOpsClient, parse_documents

FIXTURES = Path(__file__).parents[1] / "fixtures" / "epo"


def xml(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


class FakeTime:
    def __init__(self) -> None:
        self.now = 0.0
        self.waits: list[float] = []

    def clock(self) -> float:
        return self.now

    async def sleep(self, duration: float) -> None:
        self.waits.append(duration)
        self.now += duration


def test_xml_normalization_and_missing_fields() -> None:
    documents = parse_documents(xml("search.xml"))
    assert [item.external_id for item in documents] == ["EP.1000000.A1", "WO.2024123456.A1"]
    assert documents[0].title == "Temperature sensor"
    assert documents[0].abstract == "A sensor measures temperature."
    assert documents[0].publication_date is not None
    assert documents[0].publication_date.isoformat() == "2000-05-17"
    assert documents[0].source_url == (
        "https://worldwide.espacenet.com/patent/search?q=pn%3DEP1000000A1"
    )
    assert documents[1].field_status["abstract"] == FieldStatus.MISSING
    assert documents[1].field_status["claims"] == FieldStatus.NOT_REQUESTED


def test_search_fetch_token_expiry_and_fulltext_availability(caplog) -> None:  # type: ignore[no-untyped-def]
    time = FakeTime()
    calls: list[str] = []
    tokens = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal tokens
        calls.append(request.url.path)
        if request.url.path.endswith("/auth/accesstoken"):
            tokens += 1
            assert request.headers["Authorization"].startswith("Basic ")
            return httpx.Response(200, json={"access_token": f"token-{tokens}", "expires_in": 40})
        assert request.headers["Authorization"].startswith("Bearer token-")
        path = request.url.path
        if "/search/" in path:
            assert request.url.params["q"] == 'txt="sensor"'
            return httpx.Response(
                200,
                content=xml("search.xml"),
                headers={
                    "X-Throttling-Control": "idle (retrieval=green:200, search=yellow:20)",
                    "X-IndividualQuotaPerHour-Used": "123",
                },
            )
        if path.endswith("/biblio"):
            return httpx.Response(200, content=xml("biblio.xml"))
        if path.endswith("/abstract"):
            return httpx.Response(200, content=xml("abstract.xml"))
        if path.endswith("/fulltext"):
            return httpx.Response(200, content=xml("fulltext_inquiry.xml"))
        if path.endswith("/claims"):
            return httpx.Response(200, content=xml("claims.xml"))
        raise AssertionError(path)

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            adapter = EpoOpsClient(
                http,
                consumer_key="private-key",
                consumer_secret="private-secret",
                clock=time.clock,
                sleep=time.sleep,
            )
            found = await adapter.search("sensor")
            assert found.status == SourceStatus.OK and len(found.documents) == 2
            assert adapter.quota_used["X-IndividualQuotaPerHour-Used"] == 123
            time.now = 15
            fetched = await adapter.fetch("EP.1000000.A1", include_fulltext=True)
            assert fetched.status == SourceStatus.OK
            document = fetched.documents[0]
            assert document.abstract == "A sensor measures temperature."
            assert document.claims == "1. A temperature sensor."
            assert document.description is None
            assert document.field_status["description"] == FieldStatus.MISSING
            assert not any(path.endswith("/description") for path in calls)
            assert tokens == 2

    with caplog.at_level(logging.DEBUG):
        asyncio.run(scenario())
    assert "private-key" not in caplog.text
    assert "private-secret" not in caplog.text
    assert "token-1" not in caplog.text


def test_not_configured_empty_and_unavailable_are_distinct() -> None:
    async def scenario() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/auth/accesstoken"):
                return httpx.Response(
                    200, json={"access_token": "private-token", "expires_in": 1200}
                )
            return httpx.Response(404)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            unconfigured = EpoOpsClient(http, consumer_key=None, consumer_secret=None)
            assert (await unconfigured.search("sensor")).status == SourceStatus.NOT_CONFIGURED
            configured = EpoOpsClient(http, consumer_key="key", consumer_secret="secret")
            assert (await configured.search("sensor")).status == SourceStatus.EMPTY
            assert (await configured.fetch("EP.1000000.A1")).status == SourceStatus.EMPTY

        def unavailable(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/auth/accesstoken"):
                return httpx.Response(
                    200, json={"access_token": "private-token", "expires_in": 1200}
                )
            return httpx.Response(200, content=b"broken xml")

        async with httpx.AsyncClient(transport=httpx.MockTransport(unavailable)) as http:
            result = await EpoOpsClient(http, consumer_key="key", consumer_secret="secret").search(
                "sensor"
            )
            assert result.status == SourceStatus.UNAVAILABLE
            assert result.error_code == "invalid_xml"

    asyncio.run(scenario())


def test_credentials_are_read_from_environment(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("EPO_CONSUMER_KEY", "key")
    monkeypatch.setenv("EPO_CONSUMER_SECRET", "secret")

    async def scenario() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: httpx.Response(404))
        ) as http:
            adapter = EpoOpsClient.from_environment(http)
            assert adapter.configured

    asyncio.run(scenario())


def test_retry_throttling_and_quota_rejection() -> None:
    time = FakeTime()
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        if request.url.path.endswith("/auth/accesstoken"):
            return httpx.Response(200, json={"access_token": "private-token", "expires_in": 1200})
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "2000"})
        if calls == 2:
            return httpx.Response(200, content=xml("search.xml"))
        return httpx.Response(403, headers={"X-Rejection-Reason": "RegisteredQuotaPerWeek"})

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            adapter = EpoOpsClient(
                http,
                consumer_key="key",
                consumer_secret="secret",
                clock=time.clock,
                sleep=time.sleep,
            )
            assert (await adapter.search("sensor")).status == SourceStatus.OK
            assert time.waits == [6.0]
            rejected = await adapter.search("sensor")
            assert rejected.status == SourceStatus.UNAVAILABLE
            assert rejected.error_code == "quota_exhausted"
            assert (await adapter.search("sensor")).error_code == "quota_exhausted"
            assert calls == 3

    asyncio.run(scenario())


def test_red_throttling_header_slows_next_search() -> None:
    time = FakeTime()
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        if request.url.path.endswith("/auth/accesstoken"):
            return httpx.Response(200, json={"access_token": "private-token", "expires_in": 1200})
        calls += 1
        return httpx.Response(
            200,
            content=xml("search.xml"),
            headers={"X-Throttling-Control": "busy (retrieval=green:200, search=red:2)"},
        )

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            adapter = EpoOpsClient(
                http,
                consumer_key="key",
                consumer_secret="secret",
                clock=time.clock,
                sleep=time.sleep,
            )
            assert (await adapter.search("sensor")).status == SourceStatus.OK
            assert (await adapter.search("sensor")).status == SourceStatus.OK
            assert calls == 2
            assert time.waits == [30.0]

    asyncio.run(scenario())


def test_server_retries_are_bounded() -> None:
    time = FakeTime()
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        if request.url.path.endswith("/auth/accesstoken"):
            return httpx.Response(200, json={"access_token": "private-token", "expires_in": 1200})
        calls += 1
        return httpx.Response(503)

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            adapter = EpoOpsClient(
                http,
                consumer_key="key",
                consumer_secret="secret",
                clock=time.clock,
                sleep=time.sleep,
            )
            result = await adapter.search("sensor")
            assert result.status == SourceStatus.UNAVAILABLE
            assert result.error_code == "server_error"
            assert calls == 3

    asyncio.run(scenario())


def test_unauthorized_refresh_and_unsafe_xml() -> None:
    tokens = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal tokens
        if request.url.path.endswith("/auth/accesstoken"):
            tokens += 1
            return httpx.Response(200, json={"access_token": f"token-{tokens}", "expires_in": 1200})
        if tokens == 1:
            return httpx.Response(401)
        return httpx.Response(200, content=b'<!DOCTYPE x [<!ENTITY bad "bad">]><x/>')

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            result = await EpoOpsClient(http, consumer_key="key", consumer_secret="secret").search(
                "sensor"
            )
            assert tokens == 2
            assert result.status == SourceStatus.UNAVAILABLE
            assert result.error_code == "invalid_xml"

    asyncio.run(scenario())
