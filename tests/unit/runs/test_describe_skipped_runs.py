import unittest

from brigade.runs.describe_skipped_runs import describe_skipped_runs


class DescribeSkippedRunsTest(unittest.TestCase):
    def test_should_describe_each_skipped_run_with_its_reason(self):
        # Act
        lines = describe_skipped_runs([{"run": "20261019T090000Z-c0ffee", "reason": "its run.json is not JSON"}])

        # Assert
        self.assertEqual(lines, ["run 20261019T090000Z-c0ffee skipped, its run.json is not JSON"])
