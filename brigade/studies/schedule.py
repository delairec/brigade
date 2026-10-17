from dataclasses import dataclass
from datetime import datetime, time, timedelta

A_WEEK = timedelta(weeks=1)
DAYS_IN_A_WEEK = 7


@dataclass(frozen=True)
class IntervalSchedule:
    period: timedelta

    def has_passed_since(self, started: datetime, now: datetime) -> bool:
        return now - started >= self.period


@dataclass(frozen=True)
class ClockSchedule:
    weekdays: tuple[int, ...]
    at: time

    def has_passed_since(self, started: datetime, now: datetime) -> bool:
        return started < max(self._find_last_occurrence(weekday, now) for weekday in self.weekdays)

    def _find_last_occurrence(self, weekday: int, now: datetime) -> datetime:
        day = now.date() - timedelta(days=(now.weekday() - weekday) % DAYS_IN_A_WEEK)
        occurrence = datetime.combine(day, self.at, tzinfo=now.tzinfo)
        if occurrence > now:
            return occurrence - A_WEEK
        return occurrence
