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


def _create_entry(minute: int, run: str, role: str, shipped_budget: int | None, main_turns: int = 12) -> LedgerEntry:
    segment = dataclasses.replace(
        create_run_finished(run, main_turns=main_turns, usage=USAGE),
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
                    "segment_p50": 12,
                    "segment_p90": 12,
                    "history": [{"ts": "2026-11-01T09:02:00Z", "before": 75, "after": 60, "direction": "lowered"}],
                    "stable": False,
                },
                "remi": {
                    "shipped": 50,
                    "computed": None,
                    "applied": 50,
                    "segments": 1,
                    "restarts": 0,
                    "growth": None,
                    "restart_tokens": None,
                    "segment_p50": 12,
                    "segment_p90": 12,
                    "history": [],
                    "stable": True,
                },
            },
        )

    def test_should_give_the_cap_changes_of_a_role_in_the_order_of_their_ts_and_mark_stable_a_role_with_none(self):
        # Arrange
        reading = LedgerReading(
            entries=(
                _create_entry(0, "r1", "ada", shipped_budget=75),
                _create_entry(1, "r2", "remi", shipped_budget=50),
                LedgerEntry(
                    instant=datetime(2026, 11, 3, 14, 0, tzinfo=UTC),
                    event=BudgetApplied(
                        role="ada", before=60, after=90, segments=6, restarts=3, growth=2500.0, restart_tokens=24300.0
                    ),
                ),
                LedgerEntry(
                    instant=datetime(2026, 11, 2, 8, 30, tzinfo=UTC),
                    event=BudgetApplied(
                        role="ada", before=75, after=60, segments=5, restarts=3, growth=3000.0, restart_tokens=18000.0
                    ),
                ),
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
                    "shipped": 75,
                    "computed": None,
                    "applied": 75,
                    "segments": 1,
                    "restarts": 0,
                    "growth": None,
                    "restart_tokens": None,
                    "segment_p50": 12,
                    "segment_p90": 12,
                    "history": [
                        {"ts": "2026-11-02T08:30:00Z", "before": 75, "after": 60, "direction": "lowered"},
                        {"ts": "2026-11-03T14:00:00Z", "before": 60, "after": 90, "direction": "raised"},
                    ],
                    "stable": False,
                },
                "remi": {
                    "shipped": 50,
                    "computed": None,
                    "applied": 50,
                    "segments": 1,
                    "restarts": 0,
                    "growth": None,
                    "restart_tokens": None,
                    "segment_p50": 12,
                    "segment_p90": 12,
                    "history": [],
                    "stable": True,
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

    def test_should_give_the_percentiles_of_the_main_turns_of_the_measured_segments_of_a_role(self):
        # Arrange
        reading = LedgerReading(
            entries=(
                _create_entry(0, "r1", "ada", shipped_budget=75, main_turns=50),
                _create_entry(1, "r2", "ada", shipped_budget=75, main_turns=10),
                _create_entry(2, "r3", "ada", shipped_budget=75, main_turns=40),
                _create_entry(3, "r4", "ada", shipped_budget=75, main_turns=20),
                _create_entry(4, "r5", "ada", shipped_budget=75, main_turns=30),
            ),
            files=(),
            skipped=(),
        )

        # Act
        budgets = describe_role_budgets(reading)

        # Assert
        self.assertEqual(budgets["ada"]["segment_p50"], 30)
        self.assertEqual(budgets["ada"]["segment_p90"], 50)

    def test_should_leave_out_of_the_percentiles_a_segment_run_at_an_earlier_digest_of_the_role(self):
        # Arrange
        earlier_digest = LedgerEntry(
            instant=datetime(2026, 11, 1, 8, 0, tzinfo=UTC),
            event=dataclasses.replace(
                _create_entry(0, "r1", "ada", shipped_budget=75, main_turns=90).event, role_digest="0a0a"
            ),
        )
        reading = LedgerReading(
            entries=(earlier_digest, _create_entry(1, "r2", "ada", shipped_budget=75, main_turns=10)),
            files=(),
            skipped=(),
        )

        # Act
        budgets = describe_role_budgets(reading)

        # Assert
        self.assertEqual(budgets["ada"]["segment_p90"], 10)

    def test_should_leave_out_of_the_percentiles_a_segment_that_reported_no_usage(self):
        # Arrange
        no_usage = LedgerEntry(
            instant=datetime(2026, 11, 1, 8, 0, tzinfo=UTC),
            event=dataclasses.replace(
                _create_entry(0, "r1", "ada", shipped_budget=75, main_turns=90).event, usage=None
            ),
        )
        reading = LedgerReading(
            entries=(no_usage, _create_entry(1, "r2", "ada", shipped_budget=75, main_turns=10)),
            files=(),
            skipped=(),
        )

        # Act
        budgets = describe_role_budgets(reading)

        # Assert
        self.assertEqual(budgets["ada"]["segment_p90"], 10)

    def test_should_leave_out_of_the_percentiles_a_segment_that_reported_no_main_turns(self):
        # Arrange
        no_main_turns = LedgerEntry(
            instant=datetime(2026, 11, 1, 8, 0, tzinfo=UTC),
            event=dataclasses.replace(_create_entry(0, "r1", "ada", shipped_budget=75).event, main_turns=None),
        )
        reading = LedgerReading(
            entries=(no_main_turns, _create_entry(1, "r2", "ada", shipped_budget=75, main_turns=10)),
            files=(),
            skipped=(),
        )

        # Act
        budgets = describe_role_budgets(reading)

        # Assert
        self.assertEqual(budgets["ada"]["segment_p50"], 10)
