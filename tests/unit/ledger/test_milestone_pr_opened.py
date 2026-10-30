import unittest

from brigade.ledger.declared_events import DECLARED_EVENTS
from brigade.ledger.milestone_pr_opened import MilestonePrOpened


class MilestonePrOpenedTest(unittest.TestCase):
    def test_should_read_the_pull_request_opened_for_a_milestone(self):
        # Act
        event = MilestonePrOpened.from_document(
            {"event": "milestone.pr_opened", "project": "shop", "milestone": "M3", "pr": 88, "login": "octo-bot"}
        )

        # Assert
        self.assertEqual(event, MilestonePrOpened(project="shop", milestone="M3", pr=88, login="octo-bot"))

    def test_should_write_the_project_the_milestone_the_pull_request_and_the_login(self):
        # Arrange
        event = MilestonePrOpened(project="shop", milestone="M3", pr=88, login="octo-bot")

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(document, {"project": "shop", "milestone": "M3", "pr": 88, "login": "octo-bot"})

    def test_should_be_declared_in_the_ledger(self):
        # Act
        declared = DECLARED_EVENTS.get("milestone.pr_opened")

        # Assert
        self.assertIs(declared, MilestonePrOpened)


if __name__ == "__main__":
    unittest.main()
