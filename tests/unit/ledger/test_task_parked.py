import unittest

from brigade.ledger.task_parked import TaskParked


class TaskParkedTest(unittest.TestCase):
    def test_should_read_the_task_parked_by_a_wave(self):
        # Act
        event = TaskParked.from_document({"event": "task.parked", "wave": "tidepool_w16", "task": "TP147"})

        # Assert
        self.assertEqual(event, TaskParked(wave="tidepool_w16", task="TP147"))
