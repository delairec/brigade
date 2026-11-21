import unittest

from brigade.dashboard.format_span import format_span


class FormatSpanTest(unittest.TestCase):
    def test_should_read_a_span_the_way_a_person_says_it(self):
        # Arrange
        rows = [
            (0, "0 s"),
            (45_999, "45 s"),
            (157_000, "2 min 37 s"),
            (599_000, "9 min 59 s"),
            (600_000, "10 min"),
            (2_820_400, "47 min"),
            (3_600_000, "1 h"),
            (17_428_000, "4 h 50 min"),
            (93_780_000, "26 h 3 min"),
        ]
        for duration_ms, expected in rows:
            with self.subTest(duration_ms=duration_ms):
                # Act
                span = format_span(duration_ms)

                # Assert
                self.assertEqual(span, expected)
