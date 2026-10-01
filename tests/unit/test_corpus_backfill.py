from __future__ import annotations

import asyncio
import json
from contextlib import nullcontext
from types import SimpleNamespace
from uuid import uuid4

import scripts.corpus_backfill as backfill
from scripts.corpus_backfill import Checkpoint, CorpusPilot, RunCounts

from app.domain.source import SourceStatus


class FakeOpenAlex:
    def __init__(self, works: list[SimpleNamespace], *, fail_fetch: bool = False) -> None:
        self.works = works
        self.fail_fetch = fail_fetch
        self.search_calls = 0
        self.fetch_calls: list[str] = []

    async def search(
        self, query: str, *, per_page: int, cursor: str, filters: str | None = None
    ) -> SimpleNamespace:
        self.search_calls += 1
        return SimpleNamespace(status=SourceStatus.OK, works=tuple(self.works), next_cursor=None)

    async def fetch(self, work_id: str) -> SimpleNamespace:
        self.fetch_calls.append(work_id)
        if self.fail_fetch:
            return SimpleNamespace(
                status=SourceStatus.UNAVAILABLE, works=(), error_code="network_error"
            )
        work = next(item for item in self.works if item.external_id == work_id)
        return SimpleNamespace(status=SourceStatus.OK, works=(work,))


def _work(work_id: str, abstract: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        source="openalex",
        external_id=work_id,
        source_url=f"https://openalex.org/{work_id}",
        abstract=abstract or ("A technical abstract. " * 8),
        title=f"Paper {work_id}",
        publication_date=None,
        updated_at=None,
        doi=None,
        landing_page_url=None,
        language="en",
        authors=(),
        topics=(),
        referenced_work_ids=(),
        cited_by_count=0,
        field_status={},
    )


def _pilot(client: FakeOpenAlex, events: list[dict[str, object]]) -> CorpusPilot:
    class Forbidden:
        def __getattr__(self, name: str) -> object:
            raise AssertionError(f"dry run touched persistence: {name}")

    return CorpusPilot(
        client=client,
        session_factory=Forbidden(),
        qdrant=Forbidden(),
        embedder=Forbidden(),
        graph_index=Forbidden(),
        run_id="test-run",
        emit=events.append,
    )


def test_max_documents_and_dry_run_do_not_write() -> None:
    client = FakeOpenAlex([_work(f"W{i}") for i in range(5)])
    events: list[dict[str, object]] = []
    result = asyncio.run(
        _pilot(client, events).run(query="graphene gas sensor", max_documents=2, dry_run=True)
    )
    assert result.fetched == 2
    assert result.previewed == 2
    assert result.ingested == 0
    assert client.fetch_calls == ["W0", "W1"]
    assert [event["stage"] for event in events].count("would_ingest") == 2


def test_checkpoint_persists_progress_and_rejects_identity_drift(tmp_path) -> None:  # type: ignore[no-untyped-def]
    checkpoint_path = tmp_path / "checkpoint.json"
    identity = {"query": "graphene", "model_digest": "abc"}
    checkpoint = Checkpoint(checkpoint_path, identity)
    checkpoint.load(resume=False, run_id="test-run")
    checkpoint.state.update(cursor="cursor-2", completed=["W1"])
    checkpoint.save()

    resumed = Checkpoint(checkpoint_path, identity)
    resumed.load(resume=True, run_id=None)
    assert resumed.state["run_id"] == "test-run"
    assert resumed.state["cursor"] == "cursor-2"
    assert resumed.state["completed"] == ["W1"]
    assert json.loads(checkpoint_path.read_text(encoding="utf-8"))["identity"] == identity

    incompatible = Checkpoint(checkpoint_path, {**identity, "model_digest": "changed"})
    try:
        incompatible.load(resume=True, run_id=None)
    except ValueError as exc:
        assert str(exc) == "checkpoint configuration/version mismatch"
    else:
        raise AssertionError("incompatible checkpoint was accepted")


def test_ineligible_abstract_is_skipped_and_counted() -> None:
    client = FakeOpenAlex([_work("W1", "short"), _work("W2")])
    events: list[dict[str, object]] = []
    result = asyncio.run(_pilot(client, events).run(query="q", max_documents=1, dry_run=True))
    assert result.fetched == 2
    assert result.skipped == 1
    assert result.previewed == 1
    assert result.ingested == 0


def test_dry_run_checkpoint_is_not_persisted(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "checkpoint.json"
    checkpoint = Checkpoint(path, {"source": "openalex"}, persist=False)
    checkpoint.load(resume=False, run_id="dry-run")
    checkpoint.state["cursor"] = "next"
    checkpoint.save()
    assert not path.exists()


def test_epo_source_uses_existing_adapter_contract_in_dry_run() -> None:
    document = SimpleNamespace(
        external_id="EP.1234567.A1",
        title="Patent title",
        abstract="A patent abstract with enough text to pass the runner's quality gate. " * 2,
        country="EP",
        publication_number="1234567",
        kind="A1",
        source_url="https://example.org/patent",
        publication_date=None,
        claims=None,
        description=None,
        field_status={},
    )

    class FakeEpo:
        async def search(
            self, query: str, *, limit: int, offset: int, filters: str | None = None
        ) -> SimpleNamespace:
            assert (query, limit, offset, filters) == ("sensor", 10, 0, "pn=EP")
            return SimpleNamespace(status=SourceStatus.OK, documents=(document,), next_offset=None)

        async def fetch(self, external_id: str, *, include_fulltext: bool) -> SimpleNamespace:
            assert external_id == document.external_id
            assert include_fulltext
            return SimpleNamespace(status=SourceStatus.OK, documents=(document,))

    events: list[dict[str, object]] = []
    pilot = CorpusPilot(
        client=FakeEpo(),
        source="epo",
        session_factory=object(),
        qdrant=object(),
        embedder=object(),
        graph_index=object(),
        run_id="epo-dry-run",
        emit=events.append,
    )
    result = asyncio.run(
        pilot.run(
            query="sensor", max_documents=1, dry_run=True, batch_size=10, filters="pn=EP"
        )
    )
    assert result.fetched == result.previewed == 1
    assert result.ingested == 0
    assert events[-1]["source"] == "epo"


def test_source_all_without_epo_credentials_falls_back_to_openalex(
    monkeypatch, tmp_path, capsys
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("EPO_CONSUMER_KEY", raising=False)
    monkeypatch.delenv("EPO_CONSUMER_SECRET", raising=False)
    calls: list[tuple[str, int]] = []

    async def run_source(
        _args: object,
        *,
        source: str,
        max_documents: int,
        checkpoint_path: object,
        run_id: str,
    ) -> tuple[RunCounts, dict[str, object], str]:
        calls.append((source, max_documents))
        return RunCounts(previewed=max_documents), {"source": source}, run_id

    monkeypatch.setattr(backfill, "_run_source", run_source)
    args = SimpleNamespace(
        source="all",
        query="sensor",
        filter=None,
        max_documents=100,
        batch_size=25,
        checkpoint=str(tmp_path / "checkpoint.json"),
        stats_output=None,
        resume=False,
        dry_run=True,
        run_id="all-run",
    )
    assert asyncio.run(backfill._run(args)) == 0
    assert calls == [("openalex", 100)]
    assert '"source": "epo"' in capsys.readouterr().out


def test_fetch_failure_is_reported_without_aborting_run() -> None:
    client = FakeOpenAlex([_work("W1"), _work("W2")], fail_fetch=True)
    events: list[dict[str, object]] = []
    result = asyncio.run(_pilot(client, events).run(query="q", max_documents=1, dry_run=True))
    assert result.errors == 1
    assert client.fetch_calls == ["W1"]
    assert any(event["stage"] == "fetch_failed" for event in events)


def test_repeated_run_reuses_revision_and_index_projections(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client = FakeOpenAlex([_work("W123")])
    revision_id = uuid4()
    revisions: dict[str, object] = {}
    qdrant_points: set[object] = set()
    graph_projections: set[object] = set()
    events: list[dict[str, object]] = []

    class Sessions:
        def begin(self) -> object:
            return nullcontext(object())

        def __call__(self) -> object:
            return nullcontext(object())

    class Ingestion:
        def __init__(self, _session: object) -> None:
            pass

        def ingest(self, document: object) -> tuple[SimpleNamespace, bool]:
            external_id = document.external_id  # type: ignore[attr-defined]
            existed = external_id in revisions
            revisions[external_id] = revision_id
            return SimpleNamespace(id=revision_id), not existed

        def acknowledge(self, _revision: object, *, backend: str, **_kwargs: object) -> bool:
            return backend == "domain_graph"

    class Indexing:
        def __init__(self, _session: object, _qdrant: object, _embedder: object) -> None:
            pass

        async def index_revision(self, revision: object, *, request_id: str) -> int:
            qdrant_points.add(revision)
            return 1

    class Graph:
        async def index_revision(self, revision: object, *, request_id: str) -> SimpleNamespace:
            graph_projections.add(revision)
            return SimpleNamespace(
                fact_count=1,
                indexer_version="graph-v1",
                projection_version="graph-projection-v1",
            )

    monkeypatch.setattr(backfill, "IngestionService", Ingestion)
    monkeypatch.setattr(backfill, "IndexingService", Indexing)
    monkeypatch.setattr(backfill, "from_openalex", lambda value: value)
    pilot = CorpusPilot(
        client=client,
        session_factory=Sessions(),
        qdrant=SimpleNamespace(spec=SimpleNamespace(projection_version="embedding-v1")),
        embedder=object(),
        graph_index=Graph(),
        run_id="repeat-run",
        emit=events.append,
    )

    first = asyncio.run(pilot.run(query="q", max_documents=1, dry_run=False))
    second = asyncio.run(pilot.run(query="q", max_documents=1, dry_run=False))

    assert first.indexed == second.indexed == 1
    assert len(revisions) == len(qdrant_points) == len(graph_projections) == 1
    completions = [event for event in events if event["stage"] == "document_complete"]
    assert [event["new_revision"] for event in completions] == [True, False]
