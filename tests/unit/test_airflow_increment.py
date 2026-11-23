"""Компонентные проверки offline pipeline на локальных фикстурах и портах."""

import hashlib
import json
import sys
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.integrations.epo import parse_documents
from app.integrations.openalex import parse_work
from app.services.ingestion import canonical_external_id, chunk_sections
from app.workers.ingest import from_epo, from_openalex

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "airflow" / "dags"))
from offline_increment.pipeline import (  # noqa: E402
    Interval,
    Item,
    Limits,
    Page,
    PipelineError,
    Progress,
    RetryableError,
    Revision,
    cursor_hash,
    run,
)

INTERVAL = Interval(datetime(2025, 1, 1, tzinfo=UTC), datetime(2025, 1, 2, tzinfo=UTC))


class FakePorts:
    def __init__(self, source: str, documents: list) -> None:
        self.source = source
        self.documents = {d.external_id: d for d in documents}
        self.document_versions = {d.external_id: "v1" for d in documents}
        self.page = Page(tuple(Item(d.external_id, "v1") for d in documents), None)
        self.frozen = {}
        self.checkpoints = {}
        self.published = {}
        self.revisions = {}
        self.acks = set()
        self.project_calls = []
        self.discovery_calls = 0
        self.fail_backend = None
        self.quality_ok = True
        self.bad_document = False
        self.quota = False

    def progress(self, source, interval):
        return self.checkpoints.get((source, interval), Progress(None, False))

    def frozen_page(self, source, interval, cursor):
        return self.frozen.get((source, interval, cursor))

    def discover(self, source, interval, cursor, limit):
        self.discovery_calls += 1
        if self.quota:
            raise RetryableError("SECRET raw payload")
        return self.page

    def freeze_page(self, source, interval, cursor, page):
        return self.frozen.setdefault((source, interval, cursor), page)

    def ingest(self, source, item):
        if self.bad_document:
            raise ValueError("SECRET raw payload")
        if self.document_versions[item.external_id] != item.revision_key:
            raise ValueError("revision changed after discovery")
        doc = self.documents[item.external_id]
        normalized = from_epo(doc) if source == "epo_ops" else from_openalex(doc)
        canonical = canonical_external_id(source, normalized.external_id)
        chunks = chunk_sections(normalized.sections)
        digest = hashlib.sha256(repr(normalized).encode()).hexdigest()
        revision_id = canonical + ":" + digest
        self.revisions[revision_id] = (normalized, chunks)
        return Revision(revision_id, digest, self.published.get(canonical) != revision_id)

    def acknowledged(self, revision, backend):
        return (revision.revision_id, backend) in self.acks

    def project(self, revision, backend):
        self.project_calls.append((revision.revision_id, backend))
        if self.fail_backend == backend:
            raise RetryableError("SECRET raw payload")
        assert revision.revision_id in self.revisions
        self.acks.add((revision.revision_id, backend))

    def quality(self, revision):
        return self.quality_ok

    def commit_page(self, source, interval, cursor, page, revisions, expected_history):
        previous = self.progress(source, interval)
        assert previous.cursor_history == expected_history
        assert previous.cursor == cursor and not previous.completed
        digest = cursor_hash(cursor)
        assert digest not in previous.cursor_history
        assert page.next_cursor is None or cursor_hash(page.next_cursor) not in (
            *previous.cursor_history,
            digest,
        )
        for revision in revisions:
            assert all(
                (revision.revision_id, backend) in self.acks
                for backend in ("domain_graph", "qdrant")
            )
            self.published[revision.revision_id.split(":")[0]] = revision.revision_id
        self.checkpoints[source, interval] = Progress(
            page.next_cursor, page.next_cursor is None, (*previous.cursor_history, digest)
        )


@pytest.fixture(params=["epo_ops", "openalex"])
def fixture_ports(request):
    if request.param == "epo_ops":
        raw = (ROOT / "tests/fixtures/epo/search.xml").read_bytes()
        docs = list(parse_documents(raw))
    else:
        path = ROOT / "tests/fixtures/openalex/work_with_abstract.json"
        raw = json.loads(path.read_text("utf-8"))
        docs = [parse_work(raw)]
    return FakePorts(request.param, docs)


def test_fixtures_new_replay_changed_and_empty(fixture_ports):
    p = fixture_ports
    first = run(p, p.source, INTERVAL, Limits())
    assert first == {"stage": "complete", "pages": 1, "revisions": len(p.documents)}
    assert len(p.project_calls) == len(p.documents) * 2
    for normalized, chunks in p.revisions.values():
        assert normalized.source == p.source
        assert all(row["text"] for row in chunks)
    assert run(p, p.source, INTERVAL, Limits())["pages"] == 0
    next_interval = Interval(INTERVAL.end, INTERVAL.end + timedelta(days=1))
    assert run(p, p.source, next_interval, Limits())["revisions"] == 0
    assert len(p.project_calls) == len(p.documents) * 2
    doc = next(iter(p.documents.values()))
    p.documents[doc.external_id] = replace(doc, title="Изменённый документ")
    p.document_versions[doc.external_id] = "v2"
    p.page = Page((Item(doc.external_id, "v2"),), None)
    third = Interval(next_interval.end, next_interval.end + timedelta(days=1))
    assert run(p, p.source, third, Limits())["revisions"] == 1
    assert len(p.project_calls) == len(p.documents) * 2 + 2
    empty = Interval(third.end, third.end + timedelta(days=1))
    p.page = Page((), None)
    assert run(p, p.source, empty, Limits())["revisions"] == 0
    assert p.progress(p.source, empty).completed


@pytest.mark.parametrize("backend", ["domain_graph", "qdrant"])
def test_partial_ack_recovery_frozen_page_and_qa(fixture_ports, backend):
    p = fixture_ports
    p.fail_backend = backend
    with pytest.raises(PipelineError, match="dependency_unavailable"):
        run(p, p.source, INTERVAL, Limits(max_attempts=2))
    assert not p.progress(p.source, INTERVAL).completed
    assert not p.published
    old_calls = list(p.project_calls)
    p.page = Page((), None)
    p.fail_backend = None
    p.quality_ok = False
    with pytest.raises(PipelineError, match="quality_failed"):
        run(p, p.source, INTERVAL, Limits())
    assert not p.published
    p.quality_ok = True
    run(p, p.source, INTERVAL, Limits())
    assert p.discovery_calls == 1
    assert p.progress(p.source, INTERVAL).completed
    assert len(p.published) == len(p.documents)
    if backend == "qdrant":
        first_graph = (old_calls[0][0], "domain_graph")
        assert p.project_calls.count(first_graph) == 1


def test_failures_are_bounded_and_sanitized(fixture_ports, caplog):
    p = fixture_ports
    with pytest.raises(PipelineError, match="unsupported_source"):
        run(p, "https://secret.example", INTERVAL, Limits())
    with pytest.raises(PipelineError, match="invalid_interval"):
        run(p, p.source, Interval(INTERVAL.start, INTERVAL.start + timedelta(days=32)), Limits())
    p.quota = True
    with pytest.raises(PipelineError) as exc:
        run(p, p.source, INTERVAL, Limits(max_attempts=2))
    assert str(exc.value) == "dependency_unavailable"
    assert p.discovery_calls == 2
    assert not p.progress(p.source, INTERVAL).completed
    p.quota = False
    p.bad_document = True
    with pytest.raises(PipelineError) as exc:
        run(p, p.source, INTERVAL, Limits())
    assert str(exc.value) == "dependency_failure"
    assert "SECRET" not in caplog.text and "SECRET" not in str(exc.value)
    assert not p.progress(p.source, INTERVAL).completed


def test_invalid_page_and_limits_never_commit(fixture_ports):
    p = fixture_ports
    p.page = Page((), "next")
    with pytest.raises(PipelineError, match="invalid_page"):
        run(p, p.source, INTERVAL, Limits())
    assert not p.frozen and not p.published
    with pytest.raises(PipelineError, match="invalid_limits"):
        run(p, p.source, INTERVAL, Limits(max_attempts=0))


def test_previous_generation_survives_partial_revision(fixture_ports):
    p = fixture_ports
    run(p, p.source, INTERVAL, Limits())
    previous = p.published.copy()
    doc = next(iter(p.documents.values()))
    p.documents[doc.external_id] = replace(doc, title="Следующая версия")
    p.document_versions[doc.external_id] = "v2"
    p.page = Page((Item(doc.external_id, "v2"),), None)
    later = Interval(INTERVAL.end, INTERVAL.end + timedelta(days=1))
    p.fail_backend = "qdrant"
    with pytest.raises(PipelineError, match="dependency_unavailable"):
        run(p, p.source, later, Limits(max_attempts=1))
    assert p.published == previous
    assert not p.progress(p.source, later).completed
    p.fail_backend = None
    run(p, p.source, later, Limits())
    assert p.published != previous


def test_bounded_pages_resume_from_committed_checkpoint(fixture_ports):
    p = fixture_ports
    original = p.discover

    def discover(source, interval, cursor, limit):
        if cursor is None:
            first = original(source, interval, cursor, limit)
            return Page(first.items, "second")
        return Page((), None)

    p.discover = discover
    with pytest.raises(PipelineError, match="page_limit"):
        run(p, p.source, INTERVAL, Limits(max_pages=1))
    assert p.progress(p.source, INTERVAL) == Progress("second", False, (cursor_hash(None),))
    assert run(p, p.source, INTERVAL, Limits(max_pages=1))["stage"] == "complete"


def test_dag_callable_uses_injected_ports_and_sanitizes_failure(monkeypatch, fixture_ports):
    import importlib.util
    import types

    class FakeDag:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    airflow_module = types.ModuleType("airflow")
    airflow_module.DAG = FakeDag
    operators = types.ModuleType("airflow.operators")
    python_operator = types.ModuleType("airflow.operators.python")
    python_operator.PythonOperator = lambda **kwargs: kwargs
    pendulum = types.ModuleType("pendulum")
    pendulum.datetime = lambda *args, **kwargs: datetime(*args, tzinfo=UTC)
    for name, module in (
        ("airflow", airflow_module),
        ("airflow.operators", operators),
        ("airflow.operators.python", python_operator),
        ("pendulum", pendulum),
    ):
        monkeypatch.setitem(sys.modules, name, module)
    spec = importlib.util.spec_from_file_location(
        "fixture_dag", ROOT / "airflow/dags/public_corpus_increment.py"
    )
    dag = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dag)
    assert dag.dag.kwargs["schedule"] is None
    assert dag.dag.kwargs["default_args"]["retries"] == 0
    monkeypatch.setattr(dag, "configured_ports", lambda: fixture_ports)
    called = []

    def fake_run(ports, source, interval, limits):
        called.append((ports, source, interval))
        return {"stage": "complete", "pages": 1, "revisions": 2}

    monkeypatch.setattr(dag, "run", fake_run)
    result = dag.execute_increment(
        data_interval_start=INTERVAL.start, data_interval_end=INTERVAL.end
    )
    assert result == {"stage": "complete", "pages": 2, "revisions": 4}
    assert [item[1] for item in called] == ["epo_ops", "openalex"]

    def failed_ports():
        raise ValueError("SECRET raw payload")

    monkeypatch.setattr(dag, "configured_ports", failed_ports)
    with pytest.raises(PipelineError) as exc:
        dag.execute_increment(data_interval_start=INTERVAL.start, data_interval_end=INTERVAL.end)
    assert str(exc.value) == "offline_increment_failed"
    assert exc.value.__suppress_context__


def test_stage_logs_and_safe_error_codes(fixture_ports, caplog):
    import logging

    p = fixture_ports
    caplog.set_level(logging.INFO, logger="offline_increment.pipeline")
    p.bad_document = True
    with pytest.raises(PipelineError, match="dependency_failure"):
        run(p, p.source, INTERVAL, Limits())
    assert "stage=discovery status=started" in caplog.text
    assert "stage=ingestion status=started" in caplog.text
    assert "SECRET" not in caplog.text
    p.bad_document = False
    run(p, p.source, INTERVAL, Limits())
    assert "stage=projection status=started" in caplog.text
    assert "stage=quality status=started" in caplog.text
    assert "stage=publish status=completed" in caplog.text
    assert "SECRET" not in caplog.text


def test_cursor_cycle_across_bounded_retries_never_republishes(fixture_ports, caplog):
    p = fixture_ports
    items = p.page.items
    page_map = {
        None: Page(items, "SECRET-cursor-A"),
        "SECRET-cursor-A": Page(items, "SECRET-cursor-B"),
        "SECRET-cursor-B": Page(items, "SECRET-cursor-A"),
    }
    p.discover = lambda source, interval, cursor, limit: page_map[cursor]
    limits = Limits(max_pages=1)
    for _ in range(2):
        with pytest.raises(PipelineError, match="page_limit"):
            run(p, p.source, INTERVAL, limits)
    checkpoint = p.progress(p.source, INTERVAL)
    published = p.published.copy()
    projection_calls = list(p.project_calls)
    assert checkpoint.cursor == "SECRET-cursor-B"
    assert len(checkpoint.cursor_history) == 2
    assert all("SECRET" not in value for value in checkpoint.cursor_history)
    for _ in range(2):
        with pytest.raises(PipelineError) as exc:
            run(p, p.source, INTERVAL, limits)
        assert str(exc.value) == "invalid_cursor"
        assert p.progress(p.source, INTERVAL) == checkpoint
        assert p.published == published
        assert p.project_calls == projection_calls
    assert "SECRET" not in caplog.text


def test_corrupted_or_exhausted_cursor_history_fails_closed(fixture_ports):
    p = fixture_ports
    p.checkpoints[p.source, INTERVAL] = Progress("next", False, ())
    with pytest.raises(PipelineError, match="invalid_progress"):
        run(p, p.source, INTERVAL, Limits())
    p.checkpoints[p.source, INTERVAL] = Progress("next", False, (cursor_hash(None),))
    with pytest.raises(PipelineError, match="interval_page_limit"):
        run(p, p.source, INTERVAL, Limits(max_interval_pages=1))
    assert p.discovery_calls == 0
