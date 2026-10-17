import unittest
from datetime import time, timedelta

from brigade.errors import BrigadeError
from brigade.studies.read_schedule import read_schedule
from brigade.studies.schedule import ClockSchedule, IntervalSchedule


class ReadScheduleTest(unittest.TestCase):
    def test_should_read_each_form_of_schedule(self):
        for every, expected in [
            ("5m", IntervalSchedule(period=timedelta(minutes=5))),
            ("90m", IntervalSchedule(period=timedelta(minutes=90))),
            ("1h", IntervalSchedule(period=timedelta(hours=1))),
            ("daily@09:00", ClockSchedule(weekdays=(0, 1, 2, 3, 4, 5, 6), at=time(9, 0))),
            ("mon@09:30", ClockSchedule(weekdays=(0,), at=time(9, 30))),
            ("sun@23:59", ClockSchedule(weekdays=(6,), at=time(23, 59))),
        ]:
            with self.subTest(every):
                # Act
                schedule = read_schedule(every)

                # Assert
                self.assertEqual(schedule, expected)

    def test_should_refuse_another_form_naming_it(self):
        for every, expected in [
            ("1d", "the schedule 1d is none of <n>m, <n>h, daily@HH:MM or <day>@HH:MM, day mon to sun"),
            ("0m", "the schedule 0m is none of <n>m, <n>h, daily@HH:MM or <day>@HH:MM, day mon to sun"),
            ("5", "the schedule 5 is none of <n>m, <n>h, daily@HH:MM or <day>@HH:MM, day mon to sun"),
            ("daily@9:00", "the schedule daily@9:00 is none of <n>m, <n>h, daily@HH:MM or <day>@HH:MM, day mon to sun"),
            (
                "daily@24:00",
                "the schedule daily@24:00 is none of <n>m, <n>h, daily@HH:MM or <day>@HH:MM, day mon to sun",
            ),
            ("mon@09:60", "the schedule mon@09:60 is none of <n>m, <n>h, daily@HH:MM or <day>@HH:MM, day mon to sun"),
            (
                "monday@09:00",
                "the schedule monday@09:00 is none of <n>m, <n>h, daily@HH:MM or <day>@HH:MM, day mon to sun",
            ),
        ]:
            with self.subTest(every):
                # Act
                with self.assertRaises(BrigadeError) as refusal:
                    read_schedule(every)

                # Assert
                self.assertEqual(str(refusal.exception), expected)
