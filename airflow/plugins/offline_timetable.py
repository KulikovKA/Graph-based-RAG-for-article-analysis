"""Регистрация timetable для сериализации DAG в Airflow."""

from airflow.plugins_manager import AirflowPlugin
from offline_increment.timetable import FutureCronTimetable


class OfflineTimetablePlugin(AirflowPlugin):
    name = "offline_timetable"
    timetables = [FutureCronTimetable]
