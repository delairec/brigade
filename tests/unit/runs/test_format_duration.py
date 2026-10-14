import unittest

from brigade.runs.format_duration import format_duration


class FormatDurationTest(unittest.TestCase):
    def test_should_print_the_duration_in_minutes_and_whole_seconds(self):
        for duration_ms, expected in [
            (1951531, "32m31s"),
            (59999, "0m59s"),
            (0, "0m00s"),
            (4200000, "70m00s"),
        ]:
            with self.subTest(duration_ms=duration_ms):
                # Act
                printed = format_duration(duration_ms)

                # Assert
                self.assertEqual(printed, expected)
