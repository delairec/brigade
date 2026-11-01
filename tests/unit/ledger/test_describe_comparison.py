import unittest
from datetime import UTC, date, datetime

from brigade.errors import BrigadeError
from brigade.ledger.describe_comparison import describe_comparison
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.read_ledger import LedgerReading
from brigade.system.read_day_range import DayRange
from tests.unit.ledger.create_run_finished import create_run_finished

EARLY_OCTOBER = DayRange(start=date(2026, 10, 1), end=date(2026, 10, 4))
MID_OCTOBER = DayRange(start=date(2026, 10, 5), end=date(2026, 10, 12))
NO_REFERENCE = {}
READING = LedgerReading(
    entries=(
        LedgerEntry(datetime(2026, 9, 30, 23, 59, tzinfo=UTC), create_run_finished("r0", main_steps=90)),
        LedgerEntry(
            datetime(2026, 10, 1, 0, 0, tzinfo=UTC),
            create_run_finished("r1", main_steps=20, task="TP1", steps_to_first_edit=4, oversized_output_steps=3),
        ),
        LedgerEntry(
            datetime(2026, 10, 4, 23, 59, tzinfo=UTC),
            create_run_finished("r2", main_steps=10, oversized_output_steps=0),
        ),
        LedgerEntry(datetime(2026, 10, 5, 0, 0, tzinfo=UTC), create_run_finished("r3")),
        LedgerEntry(datetime(2026, 10, 13, 0, 0, tzinfo=UTC), create_run_finished("r4", main_steps=90)),
    ),
    files=(),
    skipped=(),
)


def create_reading(*entries: LedgerEntry) -> LedgerReading:
    return LedgerReading(entries=entries, files=(), skipped=())


class DescribeComparisonTest(unittest.TestCase):
    def test_should_describe_the_runs_finished_from_the_start_day_to_the_end_day_included(self):
        # Act
        comparison = describe_comparison(READING, (EARLY_OCTOBER, MID_OCTOBER), NO_REFERENCE)

        # Assert
        self.assertEqual(
            comparison["ranges"][0],
            {
                "start": "2026-10-01",
                "end": "2026-10-04",
                "runs": 2,
                "segments": 2,
                "steps": {
                    "runs": {"measured": 2, "unmeasured": 0, "p50": 10, "p90": 20, "partial": 0},
                    "segments": {"measured": 2, "unmeasured": 0, "p50": 10, "p90": 20},
                },
                "steps_to_first_edit": {
                    "runs": {"measured": 1, "unmeasured": 1, "p50": 4, "p90": 4, "partial": 0},
                    "segments": {"measured": 1, "unmeasured": 1, "p50": 4, "p90": 4},
                },
                "oversized_output_steps": {
                    "runs": {"measured": 2, "unmeasured": 0, "p50": 0, "p90": 3, "partial": 0},
                    "segments": {"measured": 2, "unmeasured": 0, "p50": 0, "p90": 3},
                },
                "figures": {
                    "steps_to_first_edit_p50": 4,
                    "task_run_steps_p50": 20,
                    "oversized_output_steps_per_launch": 1.5,
                },
            },
        )

    def test_should_leave_out_the_runs_finished_after_the_end_day(self):
        # Act
        comparison = describe_comparison(READING, (EARLY_OCTOBER, MID_OCTOBER), NO_REFERENCE)

        # Assert
        self.assertEqual(comparison["ranges"][1]["runs"], 1)

    def test_should_give_no_figure_a_range_does_not_measure(self):
        # Act
        comparison = describe_comparison(READING, (EARLY_OCTOBER, MID_OCTOBER), NO_REFERENCE)

        # Assert
        self.assertEqual(
            comparison["ranges"][1]["figures"],
            {"steps_to_first_edit_p50": None, "task_run_steps_p50": None, "oversized_output_steps_per_launch": None},
        )

    def test_should_round_the_oversized_output_steps_per_launch_to_two_decimals(self):
        # Arrange
        reading = create_reading(
            LedgerEntry(datetime(2026, 10, 1, 9, tzinfo=UTC), create_run_finished("r1", oversized_output_steps=1)),
            LedgerEntry(datetime(2026, 10, 1, 10, tzinfo=UTC), create_run_finished("r2", oversized_output_steps=1)),
            LedgerEntry(datetime(2026, 10, 1, 11, tzinfo=UTC), create_run_finished("r3", oversized_output_steps=0)),
        )

        # Act
        comparison = describe_comparison(reading, (EARLY_OCTOBER,), {"task_run_steps_p50": 47.0})

        # Assert
        self.assertEqual(comparison["ranges"][0]["figures"]["oversized_output_steps_per_launch"], 0.67)

    def test_should_carry_the_reference_figures_it_compares_the_range_with(self):
        # Act
        comparison = describe_comparison(READING, (EARLY_OCTOBER,), {"task_run_steps_p50": 47.0})

        # Assert
        self.assertEqual(comparison["reference"], {"task_run_steps_p50": 47.0})

    def test_should_refuse_a_range_without_runs(self):
        # Arrange
        reading = create_reading(LedgerEntry(datetime(2026, 10, 5, 0, 0, tzinfo=UTC), create_run_finished("r3")))

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            describe_comparison(reading, (EARLY_OCTOBER, MID_OCTOBER), NO_REFERENCE)

        # Assert
        self.assertEqual(str(refusal.exception), "no run finished from 2026-10-01 to 2026-10-04")
