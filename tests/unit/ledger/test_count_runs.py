import unittest

from brigade.ledger.count_runs import RunCount, count_runs


class CountRunsTest(unittest.TestCase):
    def test_should_count_a_run_once_whatever_its_segments(self):
        # Arrange
        segments = [{"run": "r1", "cost_usd": 1.5}, {"run": "r1", "cost_usd": 2.0}, {"run": "r2", "cost_usd": 0.5}]

        # Act
        count = count_runs(segments)

        # Assert
        self.assertEqual(count, RunCount(runs=2, costless=0))

    def test_should_count_costless_a_run_one_segment_of_which_records_no_cost(self):
        # Arrange
        segments = [
            {"run": "r1", "cost_usd": 1.5},
            {"run": "r1"},
            {"run": "r1"},
            {"run": "r2", "cost_usd": 0.5},
            {"run": "r3"},
        ]

        # Act
        count = count_runs(segments)

        # Assert
        self.assertEqual(count, RunCount(runs=3, costless=2))

    def test_should_count_costless_a_segment_whose_cost_is_null(self):
        # Arrange
        segments = [{"run": "r1", "cost_usd": None}]

        # Act
        count = count_runs(segments)

        # Assert
        self.assertEqual(count, RunCount(runs=1, costless=1))
