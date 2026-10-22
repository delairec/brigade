import unittest

from brigade.ledger.tick_action_failed import TickActionFailed


class TickActionFailedTest(unittest.TestCase):
    def test_should_read_the_failed_action_where_it_applied_and_its_error(self):
        # Act
        event = TickActionFailed.from_document(
            {
                "event": "tick.action_failed",
                "action": "LaunchTask",
                "project": "tidepool",
                "wave": "tidepool_w16",
                "task": "T7",
                "error": "the setup of @TASK.T7 failed: false exited 1",
            }
        )

        # Assert
        self.assertEqual(
            event,
            TickActionFailed(
                action="LaunchTask",
                project="tidepool",
                wave="tidepool_w16",
                task="T7",
                error="the setup of @TASK.T7 failed: false exited 1",
            ),
        )

    def test_should_write_an_action_that_names_no_project_no_wave_and_no_task(self):
        # Arrange
        event = TickActionFailed(
            action="LaunchStudy", project=None, wave=None, task=None, error="the study health is not defined"
        )

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(
            document,
            {
                "action": "LaunchStudy",
                "project": None,
                "wave": None,
                "task": None,
                "error": "the study health is not defined",
            },
        )


if __name__ == "__main__":
    unittest.main()
