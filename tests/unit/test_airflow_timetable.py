"""Проверка календаря на настоящем Airflow, без scheduler и сети."""

from datetime import timedelta
from importlib.util import find_spec
from unittest import SkipTest
from unittest.mock import patch

if find_spec("airflow") is None or find_spec("airflow.timetables") is None:
    raise SkipTest("Требуется Airflow 2.11")
from airflow.timetables.base import DataInterval, TimeRestriction
from offline_increment import timetable
from pendulum import datetime


def test_next_schedule_after_downtime_and_manual_interval():
    clock = datetime(2026, 11, 23, 12, 0, tz="UTC")
    schedule = timetable.FutureCronTimetable(
        "0 3 * * *", timezone="Europe/Moscow", interval=timedelta(days=1)
    )
    restriction = TimeRestriction(
        earliest=datetime(2024, 1, 1, tz="UTC"), latest=None, catchup=False
    )
    previous = DataInterval(
        start=datetime(2026, 11, 18, tz="UTC"),
        end=datetime(2026, 11, 19, tz="UTC"),
    )
    with patch.object(timetable, "utcnow", return_value=clock):
        info = schedule.next_dagrun_info(
            last_automated_data_interval=previous, restriction=restriction
        )
    assert info.run_after == datetime(2026, 11, 24, tz="UTC")
    assert info.data_interval.start == datetime(2026, 11, 23, tz="UTC")
    assert info.data_interval.end == info.run_after
    manual = schedule.infer_manual_data_interval(run_after=clock)
    assert manual.start == datetime(2026, 11, 22, 12, tz="UTC")
    assert manual.end == clock


if __name__ == "__main__":
    test_next_schedule_after_downtime_and_manual_interval()
    print("PASS")
