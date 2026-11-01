import unittest

from brigade.ledger.declared_events import DECLARED_EVENTS
from brigade.ledger.milestone_pr_described import MilestonePrDescribed


class MilestonePrDescribedTest(unittest.TestCase):
    def test_should_read_the_head_at_which_the_pull_request_of_a_milestone_was_described(self):
        # Act
        event = MilestonePrDescribed.from_document(
            {
                "event": "milestone.pr_described",
                "project": "tidepool",
                "milestone": "M4",
                "pr": 81,
                "head": "9010166d",
                "login": "tidepool-cli",
            }
        )

        # Assert
        self.assertEqual(
            event,
            MilestonePrDescribed(project="tidepool", milestone="M4", pr=81, head="9010166d", login="tidepool-cli"),
        )

    def test_should_write_the_project_the_milestone_the_pull_request_the_head_and_the_login(self):
        # Arrange
        event = MilestonePrDescribed(project="tidepool", milestone="M4", pr=81, head="9010166d", login="tidepool-cli")

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(
            document, {"project": "tidepool", "milestone": "M4", "pr": 81, "head": "9010166d", "login": "tidepool-cli"}
        )

    def test_should_be_declared_in_the_ledger(self):
        # Act
        declared = DECLARED_EVENTS.get("milestone.pr_described")

        # Assert
        self.assertIs(declared, MilestonePrDescribed)


if __name__ == "__main__":
    unittest.main()
