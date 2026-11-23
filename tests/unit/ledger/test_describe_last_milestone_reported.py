import unittest
from datetime import UTC, datetime

from brigade.ledger.describe_last_milestone_reported import describe_last_milestone_reported
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.milestone_closed import MilestoneClosed
from brigade.ledger.milestone_reported import MilestoneReported
from brigade.ledger.wave_closed import WaveClosed


def at(hour: int, minute: int) -> datetime:
    return datetime(2026, 10, 19, hour, minute, tzinfo=UTC)


def report(hour: int, project: str, milestone: str) -> LedgerEntry:
    return LedgerEntry(at(hour, 0), MilestoneReported(project=project, milestone=milestone, run="r", login=None))


def close(hour: int, project: str, milestone: str) -> LedgerEntry:
    return LedgerEntry(at(hour, 0), MilestoneClosed(project=project, milestone=milestone, pr=30))


class DescribeLastMilestoneReportedTest(unittest.TestCase):
    def test_should_name_the_milestone_reported_last_its_report_and_when_it_reached_main(self):
        # Arrange
        entries = (report(1, "oak", "M1"), close(2, "oak", "M1"), report(3, "oak", "M2"), close(4, "oak", "M2"))

        # Act
        described = describe_last_milestone_reported(entries)

        # Assert
        self.assertEqual(
            described,
            {
                "project": "oak",
                "milestone": "M2",
                "report": "oak_M2",
                "reported_at": "2026-10-19T03:00:00Z",
                "reached_main_at": "2026-10-19T04:00:00Z",
            },
        )

    def test_should_leave_unreached_a_milestone_whose_pull_request_is_not_merged(self):
        # Arrange
        entries = (report(1, "oak", "M2"), close(2, "elm", "M2"), close(3, "oak", "M1"))

        # Act
        described = describe_last_milestone_reported(entries)

        # Assert
        self.assertEqual(
            described,
            {
                "project": "oak",
                "milestone": "M2",
                "report": "oak_M2",
                "reported_at": "2026-10-19T01:00:00Z",
                "reached_main_at": None,
            },
        )

    def test_should_leave_unreached_a_milestone_reported_again_after_its_merge(self):
        # Arrange
        entries = (report(1, "oak", "M2"), close(2, "oak", "M2"), report(3, "oak", "M2"))

        # Act
        described = describe_last_milestone_reported(entries)

        # Assert
        self.assertIsNone(described["reached_main_at"])

    def test_should_name_no_milestone_when_none_was_reported(self):
        # Arrange
        entries = (close(1, "oak", "M1"), LedgerEntry(at(2, 0), WaveClosed(wave="oak_w1")))

        # Act
        described = describe_last_milestone_reported(entries)

        # Assert
        self.assertIsNone(described)
