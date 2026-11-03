import unittest

from brigade.ledger.declared_events import DECLARED_EVENTS
from brigade.ledger.task_reported import TaskReported


class TaskReportedTest(unittest.TestCase):
    def test_should_read_the_report_run_of_a_task(self):
        # Act
        event = TaskReported.from_document(
            {
                "event": "task.reported",
                "project": "brigade",
                "task": "B240",
                "run": "20261102T120000Z-a1b2c3",
                "login": "brigade-cli",
            }
        )

        # Assert
        self.assertEqual(
            event, TaskReported(project="brigade", task="B240", run="20261102T120000Z-a1b2c3", login="brigade-cli")
        )

    def test_should_write_the_project_the_task_the_run_and_the_login(self):
        # Arrange
        event = TaskReported(project="brigade", task="B240", run="20261102T120000Z-a1b2c3", login="brigade-cli")

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(
            document,
            {"project": "brigade", "task": "B240", "run": "20261102T120000Z-a1b2c3", "login": "brigade-cli"},
        )

    def test_should_be_declared_in_the_ledger(self):
        # Act
        declared = DECLARED_EVENTS.get("task.reported")

        # Assert
        self.assertIs(declared, TaskReported)


if __name__ == "__main__":
    unittest.main()
