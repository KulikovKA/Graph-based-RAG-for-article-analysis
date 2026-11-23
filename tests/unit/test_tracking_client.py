"""Проверка очереди и границы REST без действующего сервера."""

import json
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from project_tracking import client


@pytest.fixture
def configuration(monkeypatch, tmp_path):
    monkeypatch.setenv("TRACKING_ENABLED", "true")
    monkeypatch.setenv("TRACKING_ALLOW_CREATE", "true")
    monkeypatch.setenv("TRACKING_OUTBOX", str(tmp_path / "outbox.sqlite"))
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    return tmp_path / "outbox.sqlite"


def test_outage_queues_and_replay_reuses_run(configuration, monkeypatch):
    monkeypatch.setattr(client, "_send", lambda event: (_ for _ in ()).throw(OSError()))
    assert client.record("retrieval_quality", "dag/private-id", {}, {}, {}) == "queued"
    with sqlite3.connect(configuration) as connection:
        payload = connection.execute("SELECT payload FROM events").fetchone()[0]
    assert "dag/private-id" not in payload
    sent = []
    monkeypatch.setattr(client, "_send", sent.append)
    assert client.replay() == 0
    assert client.record("retrieval_quality", "dag/private-id", {}, {}, {}) == "delivered"
    assert len(sent) == 1
    assert (
        client.record("retrieval_quality", "dag/private-id", {}, {}, {}, status="FAILED") == "error"
    )


def test_failed_run_can_finish_on_retry(configuration, monkeypatch):
    sent = []
    monkeypatch.setattr(client, "_send", sent.append)
    assert (
        client.record("retrieval_quality", "job-retry", {}, {}, {}, status="FAILED") == "delivered"
    )
    assert client.record("retrieval_quality", "job-retry", {}, {}, {}) == "delivered"
    assert [event["status"] for event in sent] == ["FAILED", "FINISHED"]
    assert sent[0]["event_key"] == sent[1]["event_key"]


def test_slow_server_does_not_block_another_enqueue(configuration, monkeypatch):
    started = threading.Event()
    release = threading.Event()

    def send(event):
        if event["event_key"] == first_key:
            started.set()
            assert release.wait(5)
        else:
            raise OSError()

    import hashlib

    first_key = hashlib.sha256(b"retrieval_quality\0slow").hexdigest()
    monkeypatch.setattr(client, "_send", send)
    with ThreadPoolExecutor(max_workers=2) as executor:
        future = executor.submit(client.record, "retrieval_quality", "slow", {}, {}, {})
        assert started.wait(2)
        assert client.record("retrieval_quality", "other", {}, {}, {}) == "queued"
        release.set()
        assert future.result() == "delivered"
    with sqlite3.connect(configuration) as connection:
        assert connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 2


def test_concurrent_replays_use_one_local_delivery(configuration, monkeypatch):
    monkeypatch.setattr(client, "_send", lambda event: (_ for _ in ()).throw(OSError()))
    assert client.record("retrieval_quality", "job-1", {}, {}, {}) == "queued"
    sent = []
    monkeypatch.setattr(client, "_send", sent.append)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: client.replay(), range(2)))
    assert all(result in (0, 1) for result in results)
    assert client.replay() == 0
    assert len(sent) == 1


def test_send_creates_run_logs_artifact_and_failed_status(configuration, monkeypatch):
    calls = []

    def request(method, path, payload=None):
        calls.append((method, path, payload))
        if "get-by-name" in path:
            return {"experiment": {"experiment_id": "7"}}
        if path.endswith("/runs/search"):
            return {"runs": []}
        if path.endswith("/runs/create"):
            return {
                "run": {
                    "info": {
                        "run_id": "a" * 32,
                        "artifact_uri": "mlflow-artifacts:/7/run/artifacts",
                    }
                }
            }
        return {}

    monkeypatch.setattr(client, "_request", request)
    assert client.record("retrieval_quality", "job-2", {}, {}, {}, status="FAILED") == "delivered"
    assert any(
        path.endswith("/tracking-event.json") and method == "PUT" for method, path, _ in calls
    )
    assert calls[-1][2]["status"] == "FAILED"
    assert "job-2" not in json.dumps(calls)


def test_search_existing_run_prevents_duplicate_after_crash(configuration, monkeypatch):
    calls = []

    def request(method, path, payload=None):
        calls.append(path)
        if "get-by-name" in path:
            return {"experiment": {"experiment_id": "7"}}
        if path.endswith("/runs/search"):
            return {
                "runs": [
                    {
                        "info": {
                            "run_id": "a" * 32,
                            "artifact_uri": "mlflow-artifacts:/7/run/artifacts",
                        }
                    }
                ]
            }
        return {}

    monkeypatch.setattr(client, "_request", request)
    assert client.record("retrieval_quality", "job-3", {}, {}, {}) == "delivered"
    assert not any(path.endswith("/runs/create") for path in calls)


def test_forbidden_fields_never_enter_queue(configuration, monkeypatch):
    monkeypatch.setattr(client, "_send", lambda event: None)
    assert client.record("retrieval_quality", "job-4", {"raw_prompt": "private"}, {}, {}) == "error"
    assert not configuration.exists()


def test_disabled_and_unavailable_outbox_do_not_raise(configuration, monkeypatch):
    monkeypatch.setenv("TRACKING_ENABLED", "false")
    assert client.record("retrieval_quality", "job", {}, {}, {}) == "disabled"
    monkeypatch.setenv("TRACKING_ENABLED", "true")
    monkeypatch.delenv("TRACKING_OUTBOX")
    assert client.record("retrieval_quality", "job", {}, {}, {}) == "error"


def test_queue_connection_is_closed(configuration, monkeypatch):
    monkeypatch.setattr(client, "_send", lambda event: None)
    assert client.record("retrieval_quality", "job", {}, {}, {}) == "delivered"
    configuration.unlink()
    assert not configuration.exists()


def test_schema_version_is_set_and_unknown_version_rejected(configuration, monkeypatch):
    sent = []
    monkeypatch.setattr(client, "_send", sent.append)
    assert client.record("retrieval_quality", "version", {}, {}, {}) == "delivered"
    assert sent[0]["params"]["schema_version"] == 1
    assert client.record("retrieval_quality", "version2", {"schema_version": 2}, {}, {}) == "error"
