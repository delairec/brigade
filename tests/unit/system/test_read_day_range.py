import argparse
import unittest
from datetime import date

from brigade.system.read_day_range import DayRange, read_day_range


class ReadDayRangeTest(unittest.TestCase):
    def test_should_read_the_start_and_the_end_day(self):
        # Act
        day_range = read_day_range("2026-09-26..2026-10-03")

        # Assert
        self.assertEqual(day_range, DayRange(start=date(2026, 9, 26), end=date(2026, 10, 3)))

    def test_should_refuse_a_text_that_is_not_two_days_around_two_dots(self):
        for text in ["2026-09-26", "2026-09-26..", "..2026-10-03", "2026-09-26..soon"]:
            with self.subTest(text=text):
                # Act
                with self.assertRaises(argparse.ArgumentTypeError) as raised:
                    read_day_range(text)

                # Assert
                self.assertEqual(str(raised.exception), f"{text!r} is not a range START..END of days YYYY-MM-DD")
