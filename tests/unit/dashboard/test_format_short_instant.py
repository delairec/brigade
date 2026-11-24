import unittest

from brigade.dashboard.format_short_instant import format_short_instant


class FormatShortInstantTest(unittest.TestCase):
    def test_should_keep_the_day_and_the_minute_of_a_moment_of_the_ledger(self):
        # Act
        instant = format_short_instant("2026-11-17T20:55:42Z")

        # Assert
        self.assertEqual(instant, "2026-11-17 20:55Z")

    def test_should_read_a_moment_written_with_an_offset_in_utc(self):
        # Act
        instant = format_short_instant("2026-11-18T00:30:00+02:00")

        # Assert
        self.assertEqual(instant, "2026-11-17 22:30Z")
