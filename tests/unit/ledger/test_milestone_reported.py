import unittest

from brigade.ledger.declared_events import DECLARED_EVENTS
from brigade.ledger.milestone_reported import MilestoneReported


class MilestoneReportedTest(unittest.TestCase):
    def test_should_read_the_report_run_of_a_milestone(self):
        # Act
        event = MilestoneReported.from_document(
            {
                "event": "milestone.reported",
                "project": "brigade",
                "milestone": "M6",
                "run": "20261102T120000Z-a1b2c3",
                "login": "brigade-cli",
            }
        )

        # Assert
        self.assertEqual(
            event,
            MilestoneReported(project="brigade", milestone="M6", run="20261102T120000Z-a1b2c3", login="brigade-cli"),
        )

    def test_should_write_the_project_the_milestone_the_run_and_the_login(self):
        # Arrange
        event = MilestoneReported(project="brigade", milestone="M6", run="20261102T120000Z-a1b2c3", login="brigade-cli")

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(
            document,
            {"project": "brigade", "milestone": "M6", "run": "20261102T120000Z-a1b2c3", "login": "brigade-cli"},
        )

    def test_should_be_declared_in_the_ledger(self):
        # Act
        declared = DECLARED_EVENTS.get("milestone.reported")

        # Assert
        self.assertIs(declared, MilestoneReported)


if __name__ == "__main__":
    unittest.main()
