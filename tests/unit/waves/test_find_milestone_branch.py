import unittest
from datetime import UTC, datetime

from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.milestone_branch_cut import MilestoneBranchCut
from brigade.ledger.wave_closed import WaveClosed
from brigade.waves.find_milestone_branch import find_milestone_branch

INSTANT = datetime(2026, 10, 29, 9, 0, tzinfo=UTC)


def _record(project: str, milestone: str, branch: str) -> LedgerEntry:
    return LedgerEntry(
        instant=INSTANT, event=MilestoneBranchCut(project=project, milestone=milestone, branch=branch, login=None)
    )


class FindMilestoneBranchTest(unittest.TestCase):
    def test_should_read_the_branch_the_last_cut_of_the_milestone_records(self):
        # Arrange
        entries = (
            _record("shop", "M3", "integration/dashboard"),
            LedgerEntry(instant=INSTANT, event=WaveClosed(wave="shop_w1", pr=12)),
            _record("shop", "M3", "integration/dashboard-again"),
            _record("shop", "M4", "integration/payments"),
        )

        # Act
        branch = find_milestone_branch(entries, "shop", "M3")

        # Assert
        self.assertEqual(branch, "integration/dashboard-again")

    def test_should_ignore_the_milestone_of_the_same_name_in_another_project(self):
        # Arrange
        entries = (_record("blog", "M3", "integration/editor"),)

        # Act
        branch = find_milestone_branch(entries, "shop", "M3")

        # Assert
        self.assertIsNone(branch)
