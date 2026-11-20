import unittest
from datetime import UTC, datetime

from brigade.ledger.describe_gate_weeks import describe_gate_weeks
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.ledger.task_verdict import TaskVerdict

MONDAY_OF_WEEK_45 = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)
TUESDAY_OF_WEEK_45 = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)
WEDNESDAY_OF_WEEK_45 = datetime(2026, 11, 4, 9, 0, tzinfo=UTC)
THURSDAY_OF_WEEK_45 = datetime(2026, 11, 5, 9, 0, tzinfo=UTC)
MONDAY_OF_WEEK_46 = datetime(2026, 11, 9, 9, 0, tzinfo=UTC)
NO_ENTRY = ()


def create_verdict(task: str, pr: int, verdict: str) -> TaskVerdict:
    return TaskVerdict(
        project="shop", wave="shop_w1", task=task, pr=pr, head="c0ffee", verdict=verdict, findings=(), login=None
    )


class DescribeGateWeeksTest(unittest.TestCase):
    def test_should_present_a_week_of_two_passed_pull_requests_one_of_which_a_later_task_corrects(self):
        # Arrange
        entries = (
            LedgerEntry(instant=MONDAY_OF_WEEK_45, event=create_verdict("B1", 12, "changes")),
            LedgerEntry(instant=MONDAY_OF_WEEK_45, event=create_verdict("B2", 13, "pass")),
            LedgerEntry(instant=TUESDAY_OF_WEEK_45, event=create_verdict("B1", 12, "changes")),
            LedgerEntry(instant=WEDNESDAY_OF_WEEK_45, event=create_verdict("B1", 12, "pass")),
            LedgerEntry(
                instant=THURSDAY_OF_WEEK_45,
                event=TaskPrOpened(
                    project="shop", task="B9", wave="shop_w2", branch="fix/B9-cart", pr=20, login=None, corrects=(13,)
                ),
            ),
        )

        # Act
        weeks = describe_gate_weeks(entries)

        # Assert
        self.assertEqual(
            weeks,
            [
                {
                    "week": "2026-W45",
                    "passed": 2,
                    "escaped": 1,
                    "escape_rate": "1/2",
                    "median_rounds": 2,
                    "tasks": [{"task": "B2", "rounds": 1}, {"task": "B1", "rounds": 3}],
                }
            ],
        )

    def test_should_present_one_row_per_iso_week_of_the_pass_verdicts_oldest_first(self):
        # Arrange
        entries = (
            LedgerEntry(instant=MONDAY_OF_WEEK_45, event=create_verdict("B1", 12, "changes")),
            LedgerEntry(instant=MONDAY_OF_WEEK_45, event=create_verdict("B2", 13, "pass")),
            LedgerEntry(instant=MONDAY_OF_WEEK_46, event=create_verdict("B1", 12, "pass")),
        )

        # Act
        weeks = describe_gate_weeks(entries)

        # Assert
        self.assertEqual(
            weeks,
            [
                {
                    "week": "2026-W45",
                    "passed": 1,
                    "escaped": 0,
                    "escape_rate": "0/1",
                    "median_rounds": 1,
                    "tasks": [{"task": "B2", "rounds": 1}],
                },
                {
                    "week": "2026-W46",
                    "passed": 1,
                    "escaped": 0,
                    "escape_rate": "0/1",
                    "median_rounds": 2,
                    "tasks": [{"task": "B1", "rounds": 2}],
                },
            ],
        )

    def test_should_present_the_older_week_first_whatever_the_order_of_the_ledger_lines(self):
        # Arrange
        entries = (
            LedgerEntry(instant=MONDAY_OF_WEEK_46, event=create_verdict("B1", 12, "pass")),
            LedgerEntry(instant=MONDAY_OF_WEEK_45, event=create_verdict("B2", 13, "pass")),
        )

        # Act
        weeks = describe_gate_weeks(entries)

        # Assert
        self.assertEqual(
            weeks,
            [
                {
                    "week": "2026-W45",
                    "passed": 1,
                    "escaped": 0,
                    "escape_rate": "0/1",
                    "median_rounds": 1,
                    "tasks": [{"task": "B2", "rounds": 1}],
                },
                {
                    "week": "2026-W46",
                    "passed": 1,
                    "escaped": 0,
                    "escape_rate": "0/1",
                    "median_rounds": 1,
                    "tasks": [{"task": "B1", "rounds": 1}],
                },
            ],
        )

    def test_should_present_no_week_when_no_pull_request_passed(self):
        # Act
        weeks = describe_gate_weeks(NO_ENTRY)

        # Assert
        self.assertEqual(weeks, [])
