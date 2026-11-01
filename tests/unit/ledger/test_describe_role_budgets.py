import dataclasses
import unittest
from datetime import UTC, datetime

from brigade.ledger.budget_applied import BudgetApplied
from brigade.ledger.describe_role_budgets import describe_role_budgets
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.read_ledger import LedgerReading
from brigade.system.token_usage import TokenUsage
from tests.unit.ledger.create_run_finished import create_run_finished

USAGE = TokenUsage(input_tokens=0, output_tokens=0, cache_creation_input_tokens=0, cache_read_input_tokens=30000)


def _create_entry(minute: int, run: str, role: str, shipped_budget: int | None) -> LedgerEntry:
    segment = dataclasses.replace(
        create_run_finished(run, main_steps=12, usage=USAGE),
        role=role,
        role_digest="3f1a",
        procedure_digest="7b2e",
        shipped_budget=shipped_budget,
    )
    return LedgerEntry(instant=datetime(2026, 11, 1, 9, minute, tzinfo=UTC), event=segment)


class DescribeRoleBudgetsTest(unittest.TestCase):
    def test_should_describe_the_cap_of_each_role_at_the_budget_its_latest_segment_ships(self):
        # Arrange
        reading = LedgerReading(
            entries=(
                _create_entry(0, "r1", "ada", shipped_budget=75),
                _create_entry(1, "r2", "remi", shipped_budget=50),
                LedgerEntry(
                    instant=datetime(2026, 11, 1, 9, 2, tzinfo=UTC),
                    event=BudgetApplied(
                        role="ada", before=75, after=60, segments=1, restarts=0, growth=None, restart_tokens=None
                    ),
                ),
                _create_entry(3, "r3", "ada", shipped_budget=60),
            ),
            files=(),
            skipped=(),
        )

        # Act
        budgets = describe_role_budgets(reading)

        # Assert
        self.assertEqual(
            budgets,
            {
                "ada": {
                    "shipped": 60,
                    "computed": None,
                    "applied": 60,
                    "segments": 2,
                    "restarts": 0,
                    "growth": None,
                    "restart_tokens": None,
                },
                "remi": {
                    "shipped": 50,
                    "computed": None,
                    "applied": 50,
                    "segments": 1,
                    "restarts": 0,
                    "growth": None,
                    "restart_tokens": None,
                },
            },
        )

    def test_should_leave_out_a_role_whose_segments_record_no_shipped_budget(self):
        # Arrange
        segments_before_the_shipped_budget = LedgerReading(
            entries=(_create_entry(0, "r1", "ada", shipped_budget=None),), files=(), skipped=()
        )

        # Act
        budgets = describe_role_budgets(segments_before_the_shipped_budget)

        # Assert
        self.assertEqual(budgets, {})
