import unittest

from brigade.ledger.format_steps_lines import format_steps_lines


class FormatStepsLinesTest(unittest.TestCase):
    def test_should_format_the_run_and_segment_summaries_marking_a_missing_percentile(self):
        # Arrange
        steps = {
            "runs": {"measured": 1, "unmeasured": 2, "p50": 3, "p90": None, "partial": 0},
            "segments": {"measured": 2, "unmeasured": 0, "p50": 3, "p90": 7},
        }

        # Act
        lines = format_steps_lines("  ", steps)

        # Assert
        self.assertEqual(
            lines,
            [
                "  runs p50 3  p90 -  measured 1  partial 0  unmeasured 2",
                "  segments p50 3  p90 7  measured 2  unmeasured 0",
            ],
        )
