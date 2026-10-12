import unittest
from datetime import UTC, datetime

from brigade.runs.decide_stop_at import decide_stop_at


class DecideStopAtTest(unittest.TestCase):
    def test_should_place_the_soft_limit_the_margin_before_the_wall_time_limit_to_the_second(self):
        # Arrange
        rows = [
            ("a whole limit", datetime(2026, 10, 7, 9, 0, 0, tzinfo=UTC), 1500, 120, "2026-10-07T09:23:00Z"),
            ("a fraction dropped", datetime(2026, 10, 7, 9, 0, 0, 700000, tzinfo=UTC), 2.5, 1, "2026-10-07T09:00:02Z"),
        ]
        for case, launched_at, wall_limit_s, margin_s, expected_stop_at in rows:
            with self.subTest(case=case):
                # Act
                stop_at = decide_stop_at(launched_at, wall_limit_s, margin_s)

                # Assert
                self.assertEqual(stop_at, expected_stop_at)

    def test_should_give_no_soft_limit_to_a_wall_time_limit_not_above_the_margin(self):
        # Arrange
        rows = [("equal to the margin", 120), ("below the margin", 60)]
        for case, wall_limit_s in rows:
            with self.subTest(case=case):
                # Arrange
                launched_at = datetime(2026, 10, 7, 9, 0, 0, tzinfo=UTC)
                margin = 120

                # Act
                stop_at = decide_stop_at(launched_at, wall_limit_s, margin)

                # Assert
                self.assertIsNone(stop_at)
