import unittest
from datetime import UTC, datetime

from brigade.ledger.describe_budgets import describe_budgets
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.read_ledger import LedgerReading
from tests.unit.ledger.create_run_finished import create_run_finished


def create_reading(*events) -> LedgerReading:
    entries = tuple(
        LedgerEntry(instant=datetime(2026, 10, 10, 9, minute, tzinfo=UTC), event=event)
        for minute, event in enumerate(events)
    )
    return LedgerReading(entries=entries, files=(), skipped=())


class DescribeBudgetsTest(unittest.TestCase):
    def test_should_summarize_the_last_runs_of_each_procedure_as_an_estimate_below_five(self):
        # Arrange
        reading = create_reading(
            create_run_finished("r1", procedure="awawa-task", main_steps=10),
            create_run_finished("r2", procedure="awawa-task", main_steps=30),
            create_run_finished("r3", procedure="awawa-review", main_steps=8),
        )

        # Act
        budgets = describe_budgets(reading, 1)

        # Assert
        self.assertEqual(
            budgets,
            {
                "last": 1,
                "procedures": {
                    "awawa-review": {
                        "runs": {"measured": 1, "unmeasured": 0, "p50": 8, "p90": 8, "partial": 0},
                        "segments": {"measured": 1, "unmeasured": 0, "p50": 8, "p90": 8},
                        "estimate": True,
                    },
                    "awawa-task": {
                        "runs": {"measured": 1, "unmeasured": 0, "p50": 30, "p90": 30, "partial": 0},
                        "segments": {"measured": 1, "unmeasured": 0, "p50": 30, "p90": 30},
                        "estimate": True,
                    },
                },
            },
        )

    def test_should_drop_the_estimate_mark_from_five_measured_runs(self):
        # Arrange
        reading = create_reading(
            create_run_finished("r1", main_steps=10),
            create_run_finished("r2", main_steps=11),
            create_run_finished("r3", main_steps=12),
            create_run_finished("r4", main_steps=13),
            create_run_finished("r5", main_steps=14),
        )

        # Act
        budgets = describe_budgets(reading, 20)

        # Assert
        self.assertFalse(budgets["procedures"]["awawa-task"]["estimate"])
