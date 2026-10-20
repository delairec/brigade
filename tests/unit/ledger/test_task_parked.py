import unittest

from brigade.ledger.task_parked import TaskParked


class TaskParkedTest(unittest.TestCase):
    def test_should_read_the_task_parked_its_reason_and_its_blockers(self):
        # Act
        event = TaskParked.from_document(
            {
                "event": "task.parked",
                "wave": "tidepool_w16",
                "task": "TP147",
                "reason": "blocked",
                "blockers": ["OPEN_QUESTION.Undecided"],
            }
        )

        # Assert
        self.assertEqual(
            event,
            TaskParked(wave="tidepool_w16", task="TP147", reason="blocked", blockers=("OPEN_QUESTION.Undecided",)),
        )

    def test_should_write_the_task_parked_its_reason_and_its_blockers(self):
        # Arrange
        event = TaskParked(wave="tidepool_w16", task="TP147", reason="blocked", blockers=("OPEN_QUESTION.Undecided",))

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(
            document,
            {"wave": "tidepool_w16", "task": "TP147", "reason": "blocked", "blockers": ["OPEN_QUESTION.Undecided"]},
        )
