import argparse
import unittest
from datetime import date

from brigade.system.read_day import read_day


class ReadDayTest(unittest.TestCase):
    def test_should_read_a_day_written_year_month_day(self):
        # Act
        day = read_day("2026-10-05")

        # Assert
        self.assertEqual(day, date(2026, 10, 5))

    def test_should_refuse_a_day_the_calendar_does_not_hold(self):
        # Act
        with self.assertRaises(argparse.ArgumentTypeError) as refusal:
            read_day("2026-13-01")

        # Assert
        self.assertEqual(str(refusal.exception), "'2026-13-01' is not a day YYYY-MM-DD")
