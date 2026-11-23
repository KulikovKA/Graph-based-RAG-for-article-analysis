"""Офлайн-обновление публичного корпуса; подключение портов ожидает I-AIR."""

import hashlib
import logging
import os
import re
import time
from datetime import UTC, timedelta
from datetime import datetime as utc_datetime

from airflow import DAG
from airflow.exceptions import AirflowSkipException
from airflow.operators.python import PythonOperator
from offline_increment.pipeline import SAFE_ERRORS, Interval, Limits, PipelineError, run
from offline_increment.runtime import configured_ports
from offline_increment.timetable import FutureCronTimetable
from pendulum import datetime

logger = logging.getLogger(__name__)


def record_run(context, measurements, status, error_code):
    try:
        from project_tracking.client import record
        from project_tracking.schema import missing_metrics

        run_id = hashlib.sha256(context["run_id"].encode("utf-8")).hexdigest()
        params = {
            "dag_id": "public_corpus_increment",
            "run_id": run_id,
            "data_interval_start": context["data_interval_start"].isoformat(),
            "data_interval_end": context["data_interval_end"].isoformat(),
            "source": "mixed",
        }
        started = getattr(context.get("dag_run"), "start_date", None)
        tags = {
            "stage": {"FINISHED": "complete", "FAILED": "failed", "SKIPPED": "skipped"}[status],
            "error_code": error_code,
            "qa_status": "NOT_AVAILABLE",
            "ack_status": "NOT_AVAILABLE",

        }
        unavailable = missing_metrics("data_expansion", measurements)
        if unavailable:
            tags["unavailable_fields"] = ",".join(unavailable)
        if started is not None:
            tags["execution_timestamp"] = started.isoformat()
        outcome = record(
            "data_expansion", run_id, params=params, metrics=measurements, tags=tags,
            status="FINISHED" if status == "SKIPPED" else status,
        )
        if outcome == "error":
            logger.error("tracking_event_failed")
    except Exception:
        logger.error("tracking_event_failed")


def execute_increment(**context: object) -> dict[str, int | str]:
    # Источники и лимиты задаёт оператор. Конфигурация ручного запуска не используется.
    started = time.monotonic()
    measurements = {}
    totals: dict[str, int | str] = {"stage": "complete", "pages": 0, "revisions": 0}
    status = "FAILED"
    error_code = "offline_increment_failed"
    try:
        dag_run = context.get("dag_run")
        if getattr(dag_run, "run_type", None) == "scheduled":
            delay = utc_datetime.now(UTC) - context["data_interval_end"]
            if delay >= timedelta(days=1):
                status = "SKIPPED"
                error_code = "stale_interval"
                raise AirflowSkipException("stale_interval")
        ports = configured_ports()
        interval = Interval(context["data_interval_start"], context["data_interval_end"])
        for source in ("epo_ops", "openalex"):
            result = run(ports, source, interval, Limits())
            measurements[f"{source}_pages"] = result["pages"]
            measurements[f"{source}_revisions"] = result["revisions"]
            totals["pages"] += result["pages"]
            totals["revisions"] += result["revisions"]
        measurements["pages"] = totals["pages"]
        measurements["revisions"] = totals["revisions"]
        status = "FINISHED"
        error_code = "none"
        return totals
    except AirflowSkipException:
        raise
    except PipelineError as error:
        code = str(error)
        error_code = code if code in SAFE_ERRORS else "offline_increment_failed"
        raise PipelineError(error_code) from None
    except Exception:
        # Airflow пишет исключения в лог. Возвращаем только безопасный код.
        raise PipelineError("offline_increment_failed") from None
    finally:
        measurements["pipeline_seconds"] = time.monotonic() - started
        record_run(context, measurements, status, error_code)


cron = os.getenv("PUBLIC_CORPUS_CRON", "0 3 * * *")
if not re.fullmatch(r"(?:[0-5]?\d) (?:[01]?\d|2[0-3]) \* \* \*", cron):
    raise ValueError("PUBLIC_CORPUS_CRON должен задавать ежедневное время")

with DAG(
    dag_id="public_corpus_increment",
    start_date=datetime(2024, 1, 1, tz="Europe/Moscow"),
    schedule=FutureCronTimetable(cron, timezone="Europe/Moscow", interval=timedelta(days=1)),
    is_paused_upon_creation=True,
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 0, "execution_timeout": timedelta(minutes=30)},
) as dag:
    PythonOperator(task_id="increment", python_callable=execute_increment, do_xcom_push=True)
