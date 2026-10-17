import re
from datetime import time, timedelta

from brigade.errors import BrigadeError
from brigade.studies.schedule import ClockSchedule, IntervalSchedule

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
EVERY_DAY = "daily"
SCHEDULE = re.compile(
    r"(?:(?P<minutes>[1-9]\d*)m|(?P<hours>[1-9]\d*)h"
    rf"|(?P<day>{EVERY_DAY}|{'|'.join(DAYS)})@(?P<hour>[01]\d|2[0-3]):(?P<minute>[0-5]\d))"
)


def read_schedule(every: str) -> IntervalSchedule | ClockSchedule:
    form = SCHEDULE.fullmatch(every)
    if form is None:
        raise BrigadeError(
            f"the schedule {every} is none of <n>m, <n>h, daily@HH:MM or <day>@HH:MM, day {DAYS[0]} to {DAYS[-1]}"
        )
    if form["minutes"] is not None:
        return IntervalSchedule(period=timedelta(minutes=int(form["minutes"])))
    if form["hours"] is not None:
        return IntervalSchedule(period=timedelta(hours=int(form["hours"])))
    weekdays = tuple(range(len(DAYS))) if form["day"] == EVERY_DAY else (DAYS.index(form["day"]),)
    return ClockSchedule(weekdays=weekdays, at=time(int(form["hour"]), int(form["minute"])))
