"""Ограниченный клиент MLflow с устойчивой локальной очередью."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sqlite3
import time
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen

from project_tracking.schema import EXPERIMENTS, validate

LOGGER = logging.getLogger(__name__)


def _enabled(name: str) -> bool:
    return os.getenv(name, "").lower() in {"1", "true", "yes"}


def _uri() -> str:
    uri = os.environ["MLFLOW_TRACKING_URI"].rstrip("/")
    parsed = urlsplit(uri)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("invalid tracking URI")
    return uri


def _request(method: str, path: str, payload: object | None = None) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload, allow_nan=False).encode("utf-8")
    request = Request(_uri() + path, data=body, method=method)
    if body is not None:
        request.add_header("Content-Type", "application/json")
    with urlopen(request, timeout=3) as response:
        data = response.read()
    return json.loads(data) if data else {}


def _experiment(name: str) -> str:
    path = "/api/2.0/mlflow/experiments/get-by-name?" + urlencode({"experiment_name": name})
    try:
        return str(_request("GET", path)["experiment"]["experiment_id"])
    except HTTPError as error:
        if error.code != 404 or not _enabled("TRACKING_ALLOW_CREATE"):
            raise
    try:
        return str(
            _request("POST", "/api/2.0/mlflow/experiments/create", {"name": name})["experiment_id"]
        )
    except HTTPError as error:
        # Соседний клиент мог создать эксперимент после проверки.
        if error.code not in {400, 409}:
            raise
        return str(_request("GET", path)["experiment"]["experiment_id"])


def initialize() -> bool:
    """Создать известные эксперименты, если инициализация разрешена."""
    if not _enabled("TRACKING_ENABLED") or not _enabled("TRACKING_ALLOW_CREATE"):
        return False
    try:
        for name in EXPERIMENTS:
            _experiment(name)
        return True
    except Exception:
        LOGGER.warning("Не удалось инициализировать MLflow")
        return False


@contextmanager
def _connection() -> Iterator[sqlite3.Connection]:
    path = Path(os.environ["TRACKING_OUTBOX"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, timeout=5)) as connection, connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS events ("
            "event_key TEXT PRIMARY KEY, payload TEXT NOT NULL, "
            "delivered INTEGER NOT NULL DEFAULT 0, "
            "lease_until REAL NOT NULL DEFAULT 0)"
        )
        yield connection


def _send(event: dict[str, Any]) -> None:
    experiment_id = _experiment(event["experiment"])
    identity = event["event_key"]
    response = _request(
        "POST",
        "/api/2.0/mlflow/runs/search",
        {
            "experiment_ids": [experiment_id],
            "filter": f"tags.tracking_external_hash = '{identity}'",
            "max_results": 2,
        },
    )
    runs = response.get("runs", [])
    if len(runs) > 1:
        raise RuntimeError("duplicate external identity")
    if runs:
        info = runs[0]["info"]
    else:
        run_tags = [{"key": "tracking_external_hash", "value": identity}]
        if event["parent_run_id"]:
            run_tags.append({"key": "mlflow.parentRunId", "value": event["parent_run_id"]})
        created = _request(
            "POST",
            "/api/2.0/mlflow/runs/create",
            {
                "experiment_id": experiment_id,
                "start_time": event["timestamp"],
                "tags": run_tags,
            },
        )
        info = created["run"]["info"]
    run_id = info["run_id"]
    batch = {
        "run_id": run_id,
        "params": [{"key": key, "value": str(value)} for key, value in event["params"].items()],
        "metrics": [
            {"key": key, "value": value, "timestamp": event["timestamp"], "step": 0}
            for key, value in event["metrics"].items()
        ],
        "tags": [{"key": key, "value": str(value)} for key, value in event["tags"].items()],
    }
    _request("POST", "/api/2.0/mlflow/runs/log-batch", batch)
    artifact_uri = info["artifact_uri"]
    parsed = urlsplit(artifact_uri)
    if parsed.scheme != "mlflow-artifacts" or parsed.netloc or ".." in parsed.path.split("/"):
        raise ValueError("unsupported artifact URI")
    artifact_path = quote(parsed.path.strip("/") + "/tracking-event.json", safe="/")
    _request("PUT", "/api/2.0/mlflow-artifacts/artifacts/" + artifact_path, event)
    _request(
        "POST",
        "/api/2.0/mlflow/runs/update",
        {
            "run_id": run_id,
            "status": event["status"],
            "end_time": event["timestamp"],
        },
    )


def record(
    experiment: str,
    external_id: str,
    params: dict[str, Any],
    metrics: dict[str, Any],
    tags: dict[str, Any],
    status: str = "FINISHED",
    parent_run_id: str | None = None,
) -> str:
    """Записать агрегированное событие и вернуть delivered, queued, disabled или error."""
    if not _enabled("TRACKING_ENABLED"):
        return "disabled"
    try:
        if "schema_version" in params and params["schema_version"] != 1:
            raise ValueError("unsupported schema version")
        params = {**params, "schema_version": 1}
        validate(experiment, params, metrics, tags)
        if not isinstance(external_id, str) or not external_id or len(external_id) > 1024:
            raise ValueError("invalid external identifier")
        if status not in {"FINISHED", "FAILED"}:
            raise ValueError("invalid status")
        if parent_run_id is not None and not re.fullmatch(r"[a-f0-9]{32}", parent_run_id):
            raise ValueError("invalid parent run")
        event_key = hashlib.sha256((experiment + "\0" + external_id).encode("utf-8")).hexdigest()
        event: dict[str, Any] = {
            "experiment": experiment,
            "event_key": event_key,
            "params": params,
            "metrics": metrics,
            "tags": tags,
            "status": status,
            "parent_run_id": parent_run_id,
            "timestamp": int(time.time() * 1000),
        }
        serialized = json.dumps(event, sort_keys=True, allow_nan=False)
        with _connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            previous = connection.execute(
                "SELECT payload, delivered FROM events WHERE event_key = ?", (event_key,)
            ).fetchone()
            if previous:
                original = json.loads(previous[0])
                # Повтор одинакового события сохраняет исходную временную метку.
                event["timestamp"] = original["timestamp"]
                if event == original and previous[1]:
                    return "delivered"
                if event != original:
                    if original["status"] != "FAILED":
                        raise ValueError("completed event cannot be changed")
                    event["timestamp"] = max(int(time.time() * 1000), original["timestamp"] + 1)
                    if any(event["params"].get(k) != v for k, v in original["params"].items()):
                        raise ValueError("existing parameters cannot be changed")
                    connection.execute(
                        "UPDATE events SET payload = ?, delivered = 0 WHERE event_key = ?",
                        (json.dumps(event, sort_keys=True, allow_nan=False), event_key),
                    )
            else:
                connection.execute(
                    "INSERT INTO events(event_key, payload) VALUES (?, ?)", (event_key, serialized)
                )
            connection.commit()
        return "delivered" if _deliver(event_key) else "queued"
    except Exception:
        LOGGER.warning("Не удалось сохранить событие MLflow; проверьте конфигурацию и очередь")
        return "error"


def _deliver(event_key: str) -> bool:
    try:
        with _connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT payload, delivered, lease_until FROM events WHERE event_key = ?",
                (event_key,),
            ).fetchone()
            if row is None or row[1]:
                return bool(row)
            if row[2] > time.time():
                return False
            connection.execute(
                "UPDATE events SET lease_until = ? WHERE event_key = ?",
                (time.time() + 60, event_key),
            )
            connection.commit()
        try:
            _send(json.loads(row[0]))
        except Exception:
            with _connection() as connection:
                connection.execute(
                    "UPDATE events SET lease_until = 0 WHERE event_key = ?", (event_key,)
                )
            raise
        with _connection() as connection:
            connection.execute(
                "UPDATE events SET delivered = CASE WHEN payload = ? THEN 1 ELSE 0 END, "
                "lease_until = 0 WHERE event_key = ?",
                (row[0], event_key),
            )
            connection.commit()
            return bool(
                connection.execute(
                    "SELECT delivered FROM events WHERE event_key = ?", (event_key,)
                ).fetchone()[0]
            )
    except Exception:
        LOGGER.warning("Событие MLflow ожидает повторной отправки")
        return False


def replay() -> int:
    """Повторить ожидающие события. Возвращает число оставшихся в очереди."""
    if not _enabled("TRACKING_ENABLED"):
        return 0
    try:
        with _connection() as connection:
            keys = [
                row[0]
                for row in connection.execute(
                    "SELECT event_key FROM events WHERE delivered = 0 ORDER BY rowid"
                )
            ]
        return sum(not _deliver(key) for key in keys)
    except Exception:
        LOGGER.warning("Не удалось прочитать очередь MLflow")
        return -1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Управление очередью MLflow")
    parser.add_argument("action", choices=("initialize", "replay"))
    args = parser.parse_args()
    if args.action == "initialize":
        raise SystemExit(0 if initialize() else 1)
    remaining = replay()
    print(f"Осталось событий в очереди: {remaining}")
    raise SystemExit(0 if remaining == 0 else 1)
