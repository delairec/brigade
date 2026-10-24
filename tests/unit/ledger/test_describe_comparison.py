import unittest
from datetime import UTC, date, datetime

from brigade.errors import BrigadeError
from brigade.ledger.describe_comparison import describe_comparison
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.read_ledger import LedgerReading
from tests.unit.ledger.create_run_finished import create_run_finished

EARLIER = LedgerEntry(
    instant=datetime(2026, 10, 1, 9, 0, tzinfo=UTC), event=create_run_finished("r1", steps_to_first_edit=4)
)
LATER = LedgerEntry(instant=datetime(2026, 10, 10, 9, 0, tzinfo=UTC), event=create_run_finished("r2"))
BOUNDARY = date(2026, 10, 5)


def create_reading(*entries: LedgerEntry) -> LedgerReading:
    return LedgerReading(entries=entries, files=(), skipped=())


class DescribeComparisonTest(unittest.TestCase):
    def test_should_describe_the_runs_finished_from_the_boundary_on(self):
        # Act
        comparison = describe_comparison(create_reading(EARLIER, LATER), BOUNDARY)

        # Assert
        self.assertEqual(
            comparison["periods"]["from"],
            {
                "runs": 1,
                "segments": 1,
                "steps": {
                    "runs": {"measured": 0, "unmeasured": 1, "p50": None, "p90": None, "partial": 0},
                    "segments": {"measured": 0, "unmeasured": 1, "p50": None, "p90": None},
                },
                "steps_to_first_edit": None,
                "oversized_output_steps": None,
            },
        )

    def test_should_date_a_run_by_its_last_segment_and_count_its_segments_with_it(self):
        # Arrange
        first_segment = LedgerEntry(
            instant=datetime(2026, 10, 4, 9, 0, tzinfo=UTC), event=create_run_finished("r3", segment=1, main_steps=10)
        )
        last_segment = LedgerEntry(
            instant=datetime(2026, 10, 6, 9, 0, tzinfo=UTC), event=create_run_finished("r3", segment=2)
        )

        # Act
        comparison = describe_comparison(create_reading(EARLIER, first_segment, last_segment), BOUNDARY)

        # Assert
        self.assertEqual(
            comparison["periods"]["from"],
            {
                "runs": 1,
                "segments": 2,
                "steps": {
                    "runs": {"measured": 1, "unmeasured": 0, "p50": 10, "p90": 10, "partial": 1},
                    "segments": {"measured": 1, "unmeasured": 1, "p50": 10, "p90": 10},
                },
                "steps_to_first_edit": None,
                "oversized_output_steps": None,
            },
        )

    def test_should_report_a_measure_the_period_measured(self):
        # Act
        comparison = describe_comparison(create_reading(EARLIER, LATER), BOUNDARY)

        # Assert
        self.assertEqual(
            comparison["periods"]["before"]["steps_to_first_edit"]["segments"],
            {"measured": 1, "unmeasured": 0, "p50": 4, "p90": 4},
        )

    def test_should_refuse_a_period_without_runs(self):
        for entries, message in [
            ((LATER,), "no run finished before 2026-10-05"),
            ((EARLIER,), "no run finished from 2026-10-05 on"),
        ]:
            with self.subTest(message=message):
                # Act
                with self.assertRaises(BrigadeError) as refusal:
                    describe_comparison(create_reading(*entries), BOUNDARY)

                # Assert
                self.assertEqual(str(refusal.exception), message)
