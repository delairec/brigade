import unittest

from brigade.ledger.declared_events import DECLARED_EVENTS
from brigade.ledger.milestone_rebased import MilestoneRebased


class MilestoneRebasedTest(unittest.TestCase):
    def test_should_read_the_rebase_of_a_milestone_branch_with_its_heads_and_its_rebased_waves(self):
        # Act
        event = MilestoneRebased.from_document(
            {
                "event": "milestone.rebased",
                "project": "shop",
                "milestone": "M3",
                "branch": "integration/dashboard",
                "before": "5e2a7c1",
                "after": "9b41d08",
                "waves": ["shop_w1"],
                "login": "octo-bot",
            }
        )

        # Assert
        self.assertEqual(
            event,
            MilestoneRebased(
                project="shop",
                milestone="M3",
                branch="integration/dashboard",
                before="5e2a7c1",
                after="9b41d08",
                waves=("shop_w1",),
                login="octo-bot",
            ),
        )

    def test_should_write_the_milestone_branch_its_heads_before_and_after_its_rebased_waves_and_the_login(self):
        # Arrange
        event = MilestoneRebased(
            project="shop",
            milestone="M3",
            branch="integration/dashboard",
            before="5e2a7c1",
            after="9b41d08",
            waves=("shop_w1",),
            login=None,
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
                "before": "5e2a7c1",
                "after": "9b41d08",
                "waves": ["shop_w1"],
                "login": None,
            },
        )

    def test_should_be_declared_in_the_ledger(self):
        # Act
        declared = DECLARED_EVENTS.get("milestone.rebased")

        # Assert
        self.assertIs(declared, MilestoneRebased)
