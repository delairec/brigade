import unittest

from brigade.ledger.declared_events import DECLARED_EVENTS
from brigade.ledger.milestone_rebase_launched import MilestoneRebaseLaunched


class MilestoneRebaseLaunchedTest(unittest.TestCase):
    def test_should_read_the_launch_of_a_rebase_run_of_a_milestone_branch_with_the_heads_it_starts_from(self):
        # Act
        event = MilestoneRebaseLaunched.from_document(
            {
                "event": "milestone.rebase_launched",
                "project": "shop",
                "milestone": "M3",
                "branch": "integration/dashboard",
                "run": "20261111T090000Z-1a2b3c",
                "main_head": "7d3f9a2",
                "branch_head": "5e2a7c1",
            }
        )

        # Assert
        self.assertEqual(
            event,
            MilestoneRebaseLaunched(
                project="shop",
                milestone="M3",
                branch="integration/dashboard",
                run="20261111T090000Z-1a2b3c",
                main_head="7d3f9a2",
                branch_head="5e2a7c1",
            ),
        )

    def test_should_write_the_milestone_branch_the_run_and_the_heads_of_the_main_branch_and_the_milestone_branch(self):
        # Arrange
        event = MilestoneRebaseLaunched(
            project="shop",
            milestone="M3",
            branch="integration/dashboard",
            run="20261111T090000Z-1a2b3c",
            main_head="7d3f9a2",
            branch_head="5e2a7c1",
        )

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(
            document,
            {
                "project": "shop",
                "milestone": "M3",
                "branch": "integration/dashboard",
                "run": "20261111T090000Z-1a2b3c",
                "main_head": "7d3f9a2",
                "branch_head": "5e2a7c1",
            },
        )

    def test_should_be_declared_in_the_ledger(self):
        # Act
        declared = DECLARED_EVENTS.get("milestone.rebase_launched")

        # Assert
        self.assertIs(declared, MilestoneRebaseLaunched)
