import unittest

from brigade.ledger.task_state import TaskState
from brigade.system.validate_document import DocumentInvalid


class TaskStateTest(unittest.TestCase):
    def test_should_read_the_state_of_a_task_in_its_wave(self):
        # Act
        event = TaskState.from_document({"event": "task.state", "wave": "M1", "task": "S3", "state": "pr_open"})

        # Assert
        self.assertEqual(event, TaskState(wave="M1", task="S3", state="pr_open"))

    def test_should_write_the_wave_the_task_and_its_state(self):
        # Arrange
        event = TaskState(wave="M1", task="S3", state="paused:quota")

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(document, {"wave": "M1", "task": "S3", "state": "paused:quota"})

    def test_should_read_the_reason_a_task_is_parked_for(self):
        # Act
        event = TaskState.from_document(
            {"event": "task.state", "wave": "shop_w1", "task": "S3", "state": "parked", "reason": "pull request closed"}
        )

        # Assert
        self.assertEqual(event, TaskState(wave="shop_w1", task="S3", state="parked", reason="pull request closed"))

    def test_should_write_the_reason_a_task_is_parked_for(self):
        # Arrange
        event = TaskState(wave="shop_w1", task="S3", state="parked", reason="pull request closed")

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(
            document, {"wave": "shop_w1", "task": "S3", "state": "parked", "reason": "pull request closed"}
        )

    def test_should_refuse_a_state_the_task_diagram_does_not_hold(self):
        # Act
        with self.assertRaises(DocumentInvalid) as refusal:
            TaskState(wave="M1", task="S3", state="abandoned")

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "the task state abandoned is none of queued, running, pr_open, verifying, verified, merged,"
            " changes_requested, fixing, parked, paused:quota",
        )
