import unittest

from brigade.ledger.declared_events import DECLARED_EVENTS
from brigade.ledger.milestone_branch_cut import MilestoneBranchCut


class MilestoneBranchCutTest(unittest.TestCase):
    def test_should_read_the_branch_cut_for_a_milestone(self):
        # Act
        event = MilestoneBranchCut.from_document(
            {
                "event": "milestone.branch_cut",
                "project": "shop",
                "milestone": "M3",
                "branch": "integration/dashboard",
                "login": "octo-bot",
            }
        )

        # Assert
        self.assertEqual(
            event, MilestoneBranchCut(project="shop", milestone="M3", branch="integration/dashboard", login="octo-bot")
        )

    def test_should_write_the_project_the_milestone_the_branch_and_the_login(self):
        # Arrange
        event = MilestoneBranchCut(project="shop", milestone="M3", branch="integration/dashboard", login=None)

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(
            document, {"project": "shop", "milestone": "M3", "branch": "integration/dashboard", "login": None}
        )

    def test_should_be_declared_in_the_ledger(self):
        # Act
        declared = DECLARED_EVENTS.get("milestone.branch_cut")

        # Assert
        self.assertIs(declared, MilestoneBranchCut)
