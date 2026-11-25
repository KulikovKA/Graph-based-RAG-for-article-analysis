"""Изолированная проверка durable барьера без рабочих индексов."""

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "airflow" / "dags"))
from offline_increment.pipeline import Interval, Item, Page, Progress, cursor_hash  # noqa: E402
from offline_increment.postgres_state import PostgresPageState, StateConflict  # noqa: E402

VERSIONS = {"domain_graph": "graph1", "qdrant": "vec1", "qa": "qa1"}

pytestmark = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="нет тестовой БД")


@pytest.fixture
def state():
    url = os.environ["TEST_DATABASE_URL"]
    admin = create_engine(url)
    schema = "air_test_" + uuid4().hex
    with admin.begin() as c:
        c.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped = create_engine(url + ("&" if "?" in url else "?") + f"options=-csearch_path%3D{schema}")
    store = PostgresPageState(scoped, "cfg1", VERSIONS)
    store.initialize()
    try:
        yield store
    finally:
        scoped.dispose()
        with admin.begin() as c:
            c.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def test_restart_cas_receipts_and_unknown_commit_replay(state):
    interval = Interval(datetime(2025, 1, 1, tzinfo=UTC), datetime(2025, 1, 2, tzinfo=UTC))
    page = Page((Item("W1", "v1"),), None)
    revisions = {json.dumps(["W1", "v1"], separators=(",", ":")): "revision1"}
    versions = dict(VERSIONS)
    state.freeze("openalex", interval, None, page, revisions, "gen1")
    state.receipt("openalex", interval, None, "revision1", "domain_graph", "graph1", "gen1")
    state.engine.dispose()
    restarted = PostgresPageState(state.engine, "cfg1", VERSIONS)
    assert restarted.prepared("openalex", interval, None) == (page, revisions, "gen1")
    assert restarted.frozen_page("openalex", interval, None) == page
    restarted.freeze("openalex", interval, None, page, revisions, "gen1")
    with pytest.raises(StateConflict):
        restarted.freeze(
            "openalex", interval, None, Page((Item("W1", "v2"),), None), revisions, "gen1"
        )
    with pytest.raises(StateConflict):
        restarted.commit("openalex", interval, None, page, revisions, (), None, "gen1", versions)
    restarted.receipt("openalex", interval, None, "revision1", "qdrant", "wrong", "gen1")
    restarted.receipt("openalex", interval, None, "revision1", "qa", "qa1", "gen1")
    with pytest.raises(StateConflict):
        restarted.commit("openalex", interval, None, page, revisions, (), None, "gen1", versions)
    restarted.receipt("openalex", interval, None, "revision1", "qdrant", "vec1", "gen1")
    with pytest.raises(StateConflict):
        restarted.commit(
            "openalex", interval, None, page, revisions, ("bad",), None, "gen1", versions
        )
    with pytest.raises(StateConflict):
        restarted.commit("openalex", interval, None, page, revisions, (), "stale", "gen1", versions)
    assert restarted.progress("openalex", interval) == Progress(None, False)
    restarted.commit("openalex", interval, None, page, revisions, (), None, "gen1", versions)
    restarted.engine.dispose()
    restarted.commit("openalex", interval, None, page, revisions, (), None, "gen1", versions)
    assert restarted.progress("openalex", interval) == Progress(None, True, (cursor_hash(None),))
    with restarted.engine.connect() as c:
        assert c.execute(text("SELECT generation FROM offline_catalog")).scalar_one() == "gen1"
    with pytest.raises(StateConflict):
        restarted.commit("openalex", interval, None, page, revisions, (), None, "gen2", versions)
    with pytest.raises(StateConflict):
        PostgresPageState(state.engine, "cfg2", VERSIONS).progress("openalex", interval)


def test_catalog_and_checkpoint_roll_back_together(state):
    from sqlalchemy import event

    interval = Interval(datetime(2025, 2, 1, tzinfo=UTC), datetime(2025, 2, 2, tzinfo=UTC))
    page = Page((Item("W1", "v1"),), None)
    revisions = {json.dumps(["W1", "v1"], separators=(",", ":")): "revision1"}
    state.freeze("openalex", interval, None, page, revisions, "gen1")
    for kind, version in VERSIONS.items():
        state.receipt("openalex", interval, None, "revision1", kind, version, "gen1")

    def fail_after_catalog(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("UPDATE offline_catalog"):
            raise RuntimeError("simulated lost transaction")

    event.listen(state.engine, "after_cursor_execute", fail_after_catalog)
    try:
        with pytest.raises(RuntimeError):
            state.commit("openalex", interval, None, page, revisions, (), None, "gen1", VERSIONS)
    finally:
        event.remove(state.engine, "after_cursor_execute", fail_after_catalog)
    assert state.progress("openalex", interval) == Progress(None, False)
    with state.engine.connect() as c:
        assert c.execute(text("SELECT generation FROM offline_catalog")).scalar_one() is None
    state.commit("openalex", interval, None, page, revisions, (), None, "gen1", VERSIONS)


@pytest.mark.parametrize("kind", ["domain_graph", "qdrant", "qa"])
def test_receipts_are_bound_to_prepared_generation(state, kind):
    interval = Interval(datetime(2025, 3, 1, tzinfo=UTC), datetime(2025, 3, 2, tzinfo=UTC))
    page = Page((Item("W1", "v1"), Item("W2", "v1")), None)
    revisions = {json.dumps(["W1", "v1"], separators=(",", ":")): "r1"}
    with pytest.raises(StateConflict):
        state.freeze("openalex", interval, None, page, {"foreign": "r1"}, "gen1")
    state.freeze("openalex", interval, None, page, revisions, "gen1")
    for name, version in VERSIONS.items():
        if name != kind:
            state.receipt("openalex", interval, None, "r1", name, version, "gen1")
    with pytest.raises(StateConflict):
        state.receipt("openalex", interval, None, "r1", kind, VERSIONS[kind], "other")
    with pytest.raises(StateConflict):
        state.commit("openalex", interval, None, page, revisions, (), None, "gen1", VERSIONS)
    with pytest.raises(StateConflict):
        state.freeze("openalex", interval, None, page, revisions, "other")
    state.receipt("openalex", interval, None, "r1", kind, VERSIONS[kind], "gen1")
    with pytest.raises(StateConflict):
        state.commit("openalex", interval, None, page, revisions, (), None, "other", VERSIONS)
    state.commit("openalex", interval, None, page, revisions, (), None, "gen1", VERSIONS)


@pytest.mark.parametrize("items", [(), (Item("W1", "v1"),)])
def test_unchanged_page_preserves_catalog_and_replays(state, items):
    interval = Interval(datetime(2025, 4, 1, tzinfo=UTC), datetime(2025, 4, 2, tzinfo=UTC))
    page = Page(items, None)
    with state.engine.begin() as c:
        c.execute(text("UPDATE offline_catalog SET generation='old' WHERE id=1"))
    with pytest.raises(StateConflict):
        state.freeze("openalex", interval, None, page, {}, "")
    state.freeze("openalex", interval, None, page, {}, None)
    state.engine.dispose()
    restarted = PostgresPageState(state.engine, "cfg1", VERSIONS)
    assert restarted.frozen_page("openalex", interval, None) == page
    with pytest.raises(StateConflict):
        restarted.commit("openalex", interval, None, page, {}, (), "stale", None, VERSIONS)
    restarted.commit("openalex", interval, None, page, {}, (), "old", None, VERSIONS)
    with restarted.engine.begin() as c:
        assert c.execute(text("SELECT generation FROM offline_catalog")).scalar_one() == "old"
        c.execute(text("UPDATE offline_catalog SET generation='new' WHERE id=1"))
    restarted.commit("openalex", interval, None, page, {}, (), "old", None, VERSIONS)
    assert restarted.progress("openalex", interval) == Progress(None, True, (cursor_hash(None),))
    with restarted.engine.connect() as c:
        assert c.execute(text("SELECT generation FROM offline_catalog")).scalar_one() == "new"
    with pytest.raises(StateConflict):
        restarted.commit("openalex", interval, None, page, {}, (), "new", None, VERSIONS)


def test_competing_pages_have_one_cas_winner(state):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    interval = Interval(datetime(2025, 5, 1, tzinfo=UTC), datetime(2025, 5, 2, tzinfo=UTC))
    page = Page((Item("W1", "v1"),), None)
    revisions = {json.dumps(["W1", "v1"], separators=(",", ":")): "r1"}
    for source, generation in (("openalex", "a"), ("epo_ops", "b")):
        state.freeze(source, interval, None, page, revisions, generation)
        for kind, version in VERSIONS.items():
            state.receipt(source, interval, None, "r1", kind, version, generation)
    barrier = Barrier(2)

    def compete(source, generation):
        barrier.wait(timeout=10)
        try:
            state.commit(source, interval, None, page, revisions, (), None, generation, VERSIONS)
            return "ok"
        except StateConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda pair: compete(*pair), [("openalex", "a"), ("epo_ops", "b")]))
    assert sorted(results) == ["conflict", "ok"]
    with state.engine.connect() as c:
        assert c.execute(text("SELECT generation FROM offline_catalog")).scalar_one() in ("a", "b")
    assert (
        sum(state.progress(source, interval).completed for source in ("openalex", "epo_ops")) == 1
    )
