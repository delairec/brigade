import unittest
from datetime import UTC, datetime, time, timedelta, timezone

from brigade.studies.schedule import ClockSchedule, IntervalSchedule

PARIS_SUMMER = timezone(timedelta(hours=2))
TUESDAY_NOON_IN_PARIS = datetime(2026, 10, 6, 12, 0, tzinfo=PARIS_SUMMER)
EVERY_DAY = (0, 1, 2, 3, 4, 5, 6)
MONDAY = (0,)
TUESDAY = (1,)


class IntervalScheduleTest(unittest.TestCase):
    def test_should_pass_once_its_period_has_elapsed_since_the_start(self):
        for case, started, expected in [
            ("started four minutes ago", datetime(2026, 10, 6, 9, 56, tzinfo=UTC), False),
            ("started five minutes ago", datetime(2026, 10, 6, 9, 55, tzinfo=UTC), True),
            ("started an hour ago", datetime(2026, 10, 6, 9, 0, tzinfo=UTC), True),
        ]:
            with self.subTest(case):
                # Arrange
                every_five_minutes = IntervalSchedule(period=timedelta(minutes=5))

                # Act
                passed = every_five_minutes.has_passed_since(started, TUESDAY_NOON_IN_PARIS)

                # Assert
                self.assertIs(passed, expected)


class ClockScheduleTest(unittest.TestCase):
    def test_should_pass_once_its_last_hour_in_the_timezone_of_now_follows_the_start(self):
        for case, weekdays, at, started, expected in [
            (
                "daily, started before this morning",
                EVERY_DAY,
                time(9, 0),
                datetime(2026, 10, 6, 6, 59, tzinfo=UTC),
                True,
            ),
            (
                "daily, started at this morning's hour",
                EVERY_DAY,
                time(9, 0),
                datetime(2026, 10, 6, 7, 0, tzinfo=UTC),
                False,
            ),
            (
                "daily, started after this morning",
                EVERY_DAY,
                time(9, 0),
                datetime(2026, 10, 6, 8, 0, tzinfo=UTC),
                False,
            ),
            (
                "daily at an hour still to come today",
                EVERY_DAY,
                time(13, 0),
                datetime(2026, 10, 5, 10, 0, tzinfo=UTC),
                True,
            ),
            (
                "daily, started after yesterday's hour",
                EVERY_DAY,
                time(13, 0),
                datetime(2026, 10, 5, 12, 0, tzinfo=UTC),
                False,
            ),
            ("weekly, started before Monday's hour", MONDAY, time(9, 0), datetime(2026, 10, 5, 6, 0, tzinfo=UTC), True),
            ("weekly, started after Monday's hour", MONDAY, time(9, 0), datetime(2026, 10, 5, 8, 0, tzinfo=UTC), False),
            ("weekly, today at an hour to come", TUESDAY, time(13, 0), datetime(2026, 9, 29, 10, 0, tzinfo=UTC), True),
            (
                "weekly, started after last week's",
                TUESDAY,
                time(13, 0),
                datetime(2026, 9, 30, 10, 0, tzinfo=UTC),
                False,
            ),
        ]:
            with self.subTest(case):
                # Arrange
                schedule = ClockSchedule(weekdays=weekdays, at=at)

                # Act
                passed = schedule.has_passed_since(started, TUESDAY_NOON_IN_PARIS)

                # Assert
                self.assertIs(passed, expected)
