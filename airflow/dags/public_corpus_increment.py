"""Офлайн-обновление публичного корпуса; подключение портов ожидает I-AIR."""

from datetime import timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from offline_increment.pipeline import SAFE_ERRORS, Interval, Limits, PipelineError, run
from offline_increment.runtime import configured_ports
from pendulum import datetime


def execute_increment(**context: object) -> dict[str, int | str]:
    # Значения источников и лимитов заданы кодом, а не пользовательским dag_run.conf.
    try:
        ports = configured_ports()
        interval = Interval(context["data_interval_start"], context["data_interval_end"])
        totals: dict[str, int | str] = {"stage": "complete", "pages": 0, "revisions": 0}
        for source in ("epo_ops", "openalex"):
            result = run(ports, source, interval, Limits())
            totals["pages"] += result["pages"]
            totals["revisions"] += result["revisions"]
        return totals
    except PipelineError as error:
        code = str(error)
        raise PipelineError(code if code in SAFE_ERRORS else "offline_increment_failed") from None
    except Exception:
        # Airflow записывает сообщение исключения в лог; детали порта могут быть приватными.
        raise PipelineError("offline_increment_failed") from None


with DAG(
    dag_id="public_corpus_increment",
    start_date=datetime(2024, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 0, "execution_timeout": timedelta(minutes=30)},
) as dag:
    PythonOperator(task_id="increment", python_callable=execute_increment, do_xcom_push=True)
