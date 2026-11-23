"""Календарь без автоматического воспроизведения прошедших границ."""

from airflow.timetables.base import DagRunInfo
from airflow.timetables.trigger import CronTriggerTimetable
from airflow.utils.timezone import coerce_datetime, utcnow


class FutureCronTimetable(CronTriggerTimetable):
    def next_dagrun_info(self, *, last_automated_data_interval, restriction):
        if restriction.catchup:
            return super().next_dagrun_info(
                last_automated_data_interval=last_automated_data_interval,
                restriction=restriction,
            )
        now = coerce_datetime(utcnow())
        candidates = [self._get_next(now)]
        if restriction.earliest is not None:
            candidates.append(self._align_to_next(restriction.earliest))
        if last_automated_data_interval is not None:
            candidates.append(self._get_next(last_automated_data_interval.end))
        end = max(candidates)
        if restriction.latest is not None and end > restriction.latest:
            return None
        return DagRunInfo.interval(end - self._interval, end)
