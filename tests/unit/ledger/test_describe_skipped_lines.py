import unittest

from brigade.ledger.describe_skipped_lines import describe_skipped_lines


class DescribeSkippedLinesTest(unittest.TestCase):
    def test_should_describe_each_skipped_line_with_its_place_and_reason(self):
        # Arrange
        document = {"skipped": [{"file": "/state/ledger/2026-10.jsonl", "line": 3, "reason": "not JSON"}]}

        # Act
        lines = describe_skipped_lines(document)

        # Assert
        self.assertEqual(lines, ["skipped /state/ledger/2026-10.jsonl:3: not JSON"])
