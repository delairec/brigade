import unittest
from datetime import UTC, datetime

from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.list_passed_pull_requests import PassedPullRequest, list_passed_pull_requests
from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.ledger.task_verdict import TaskVerdict

FIRST_VERDICT = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)
SECOND_VERDICT = datetime(2026, 11, 2, 10, 0, tzinfo=UTC)
THIRD_VERDICT = datetime(2026, 11, 2, 11, 0, tzinfo=UTC)
LATER = datetime(2026, 11, 4, 9, 0, tzinfo=UTC)


def create_verdict(pr: int | None, verdict: str) -> TaskVerdict:
    return TaskVerdict(
        project="shop", wave="shop_w1", task="B1", pr=pr, head="c0ffee", verdict=verdict, findings=(), login=None
    )


def create_correction(corrects: tuple[int, ...]) -> TaskPrOpened:
    return TaskPrOpened(
        project="shop", task="B9", wave="shop_w2", branch="fix/B9-the-cart", pr=20, login=None, corrects=corrects
    )


class ListPassedPullRequestsTest(unittest.TestCase):
    def test_should_count_three_rounds_to_pass_for_a_pull_request_passed_at_its_third_verdict(self):
        # Arrange
        entries = (
            LedgerEntry(instant=FIRST_VERDICT, event=create_verdict(12, "changes")),
            LedgerEntry(instant=SECOND_VERDICT, event=create_verdict(12, "changes")),
            LedgerEntry(instant=THIRD_VERDICT, event=create_verdict(12, "pass")),
        )

        # Act
        passed = list_passed_pull_requests(entries)

        # Assert
        self.assertEqual(
            passed, (PassedPullRequest(task="B1", pr=12, passed_at=THIRD_VERDICT, rounds=3, escaped=False),)
        )

    def test_should_count_no_verdict_after_the_first_pass(self):
        # Arrange
        entries = (
            LedgerEntry(instant=FIRST_VERDICT, event=create_verdict(12, "changes")),
            LedgerEntry(instant=SECOND_VERDICT, event=create_verdict(12, "pass")),
            LedgerEntry(instant=THIRD_VERDICT, event=create_verdict(12, "pass")),
        )

        # Act
        passed = list_passed_pull_requests(entries)

        # Assert
        self.assertEqual(
            passed, (PassedPullRequest(task="B1", pr=12, passed_at=SECOND_VERDICT, rounds=2, escaped=False),)
        )

    def test_should_list_no_pull_request_the_gate_never_passed(self):
        # Arrange
        entries = (
            LedgerEntry(instant=FIRST_VERDICT, event=create_verdict(12, "changes")),
            LedgerEntry(instant=SECOND_VERDICT, event=create_verdict(12, "changes")),
        )

        # Act
        passed = list_passed_pull_requests(entries)

        # Assert
        self.assertEqual(passed, ())

    def test_should_count_no_verdict_recorded_without_its_pull_request(self):
        # Arrange
        entries = (
            LedgerEntry(instant=FIRST_VERDICT, event=create_verdict(None, "changes")),
            LedgerEntry(instant=SECOND_VERDICT, event=create_verdict(None, "pass")),
            LedgerEntry(instant=THIRD_VERDICT, event=create_verdict(12, "pass")),
        )

        # Act
        passed = list_passed_pull_requests(entries)

        # Assert
        self.assertEqual(
            passed, (PassedPullRequest(task="B1", pr=12, passed_at=THIRD_VERDICT, rounds=1, escaped=False),)
        )

    def test_should_count_a_passed_pull_request_a_later_task_corrects_as_escaped(self):
        # Arrange
        entries = (
            LedgerEntry(instant=FIRST_VERDICT, event=create_verdict(12, "pass")),
            LedgerEntry(instant=LATER, event=create_correction((7, 12))),
        )

        # Act
        passed = list_passed_pull_requests(entries)

        # Assert
        self.assertEqual(
            passed, (PassedPullRequest(task="B1", pr=12, passed_at=FIRST_VERDICT, rounds=1, escaped=True),)
        )

    def test_should_not_count_as_escaped_a_pull_request_corrected_before_it_passed(self):
        # Arrange
        entries = (
            LedgerEntry(instant=FIRST_VERDICT, event=create_correction((12,))),
            LedgerEntry(instant=SECOND_VERDICT, event=create_verdict(12, "pass")),
        )

        # Act
        passed = list_passed_pull_requests(entries)

        # Assert
        self.assertEqual(
            passed, (PassedPullRequest(task="B1", pr=12, passed_at=SECOND_VERDICT, rounds=1, escaped=False),)
        )
