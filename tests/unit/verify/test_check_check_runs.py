import unittest

from brigade.verify.check_check_runs import check_check_runs


class CheckCheckRunsTest(unittest.TestCase):
    def test_should_fail_on_each_check_run_short_of_success(self):
        # Arrange
        check_runs = [
            {"name": "unit", "verdict": "success"},
            {"name": "lint", "verdict": "failure"},
            {"name": "coverage", "verdict": "pending"},
        ]

        # Act
        check = check_check_runs(check_runs)

        # Assert
        self.assertEqual(
            check, {"name": "checks", "verdict": "fail", "findings": ["lint: failure", "coverage: pending"]}
        )
