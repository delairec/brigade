import unittest

from brigade.dashboard.format_clock import format_clock


class FormatClockTest(unittest.TestCase):
    def test_should_keep_the_time_of_day_of_a_moment_of_the_ledger(self):
        # Act
        clock = format_clock("2026-11-18T01:00:01Z")

        # Assert
        self.assertEqual(clock, "01:00:01Z")

    def test_should_read_a_moment_written_with_an_offset_in_utc(self):
        # Act
        clock = format_clock("2026-11-18T03:00:01+02:00")

        # Assert
        self.assertEqual(clock, "01:00:01Z")
