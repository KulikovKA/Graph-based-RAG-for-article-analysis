"""Проверки моста на HTTP MockTransport, без сети и настоящих credentials."""

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from app.integrations.epo import EpoOpsClient
from app.integrations.openalex import OpenAlexClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "airflow" / "dags"))
from offline_increment.pipeline import Interval, PipelineError, RetryableError  # noqa: E402
from offline_increment.sources import SourceBridge, SourceScope  # noqa: E402

INTERVAL = Interval(datetime(2025, 2, 1, tzinfo=UTC), datetime(2025, 2, 4, tzinfo=UTC))


class FakeTime:
    def __init__(self):
        self.value = 0.0

    def clock(self):
        return self.value

    async def sleep(self, amount):
        self.value += amount


def test_source_bridges_search_fetch_pin_and_changed_revision():
    clock = FakeTime()
    calls = []
    openalex = json.loads(
        (ROOT / "tests/fixtures/openalex/work_with_abstract.json").read_text("utf-8")
    )
    changed = False

    def handler(request):
        nonlocal changed
        calls.append(request)
        if request.url.host == "api.openalex.org":
            work = dict(openalex)
            if changed:
                work["title"] = "Изменение"
            if request.url.path == "/works":
                assert request.url.params["filter"] == "from_publication_date:2024-01-01"
                return httpx.Response(
                    200, json={"meta": {"count": 1, "next_cursor": None}, "results": [work]}
                )
            return httpx.Response(200, json=work)
        if request.url.path.endswith("/auth/accesstoken"):
            return httpx.Response(200, json={"access_token": "fixture-token", "expires_in": 3600})
        if "/search/" in request.url.path:
            assert request.url.params["q"] == '(txt="sensor") AND (pn=EP)'
            body = (ROOT / "tests/fixtures/epo/search.xml").read_bytes()
        elif request.url.path.endswith("/biblio"):
            body = (ROOT / "tests/fixtures/epo/biblio.xml").read_bytes()
        elif request.url.path.endswith("/abstract"):
            body = (ROOT / "tests/fixtures/epo/abstract.xml").read_bytes()
        else:
            raise AssertionError("unexpected request")
        return httpx.Response(200, content=body)

    async def scenario():
        nonlocal changed
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            bridge = SourceBridge(
                epo=EpoOpsClient(
                    http,
                    consumer_key="fixture",
                    consumer_secret="fixture",
                    clock=clock.clock,
                    sleep=clock.sleep,
                ),
                openalex=OpenAlexClient(http, clock=clock.clock, sleep=clock.sleep),
                epo_scope=SourceScope("sensor", "pn=EP"),
                openalex_scope=SourceScope("graph", "from_publication_date:2024-01-01"),
            )
            page = await bridge.discover("epo_ops", INTERVAL, None, 1)
            assert page.items[0].external_id == "EP1000000A1"
            assert page.next_cursor == "1"
            doc = await bridge.fetch_pinned("epo_ops", page.items[0])
            assert doc.source == "epo_ops" and doc.sections
            page = await bridge.discover("openalex", INTERVAL, None, 10)
            assert page.items[0].external_id == "W1234567890"
            assert (await bridge.fetch_pinned("openalex", page.items[0])).source == "openalex"
            changed = True
            with pytest.raises(PipelineError, match="revision_changed"):
                await bridge.fetch_pinned("openalex", page.items[0])
            with pytest.raises(PipelineError, match="invalid_cursor"):
                await bridge.discover("epo_ops", INTERVAL, "https://secret.example", 1)

    asyncio.run(scenario())
    assert all(request.url.host in {"api.openalex.org", "ops.epo.org"} for request in calls)


def test_source_quota_and_limits_are_safe():
    clock = FakeTime()
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(429, headers={"Retry-After": "1"}, text="SECRET raw payload")

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            bridge = SourceBridge(
                epo=EpoOpsClient(http, consumer_key="fixture", consumer_secret="fixture"),
                openalex=OpenAlexClient(http, clock=clock.clock, sleep=clock.sleep, max_attempts=2),
                epo_scope=SourceScope("sensor"),
                openalex_scope=SourceScope("graph"),
            )
            with pytest.raises(RetryableError) as exc:
                await bridge.discover("openalex", INTERVAL, None, 1)
            assert str(exc.value) == "source_unavailable"
            assert calls == 2
            with pytest.raises(PipelineError, match="invalid_limits"):
                await bridge.discover("openalex", INTERVAL, None, 101)
            with pytest.raises(PipelineError, match="invalid_scope"):
                SourceScope("", "SECRET").validate()

    asyncio.run(scenario())
