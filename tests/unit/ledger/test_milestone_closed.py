import unittest

from brigade.ledger.declared_events import DECLARED_EVENTS
from brigade.ledger.milestone_closed import MilestoneClosed


class MilestoneClosedTest(unittest.TestCase):
    def test_should_read_the_milestone_closed_by_its_merged_pull_request(self):
        # Act
        event = MilestoneClosed.from_document(
            {"event": "milestone.closed", "project": "shop", "milestone": "M3", "pr": 88}
        )

        # Assert
        self.assertEqual(event, MilestoneClosed(project="shop", milestone="M3", pr=88))

    def test_should_write_the_project_the_milestone_and_the_pull_request(self):
        # Arrange
        event = MilestoneClosed(project="shop", milestone="M3", pr=88)

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(document, {"project": "shop", "milestone": "M3", "pr": 88})

    def test_should_be_declared_in_the_ledger(self):
        # Act
        declared = DECLARED_EVENTS.get("milestone.closed")

        # Assert
        self.assertIs(declared, MilestoneClosed)


if __name__ == "__main__":
    unittest.main()
