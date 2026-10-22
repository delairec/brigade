import unittest

from brigade.ledger.task_rebased import TaskRebased


class TaskRebasedTest(unittest.TestCase):
    def test_should_read_the_rebase_of_a_task_with_its_heads_before_and_after(self):
        # Act
        event = TaskRebased.from_document(
            {
                "event": "task.rebased",
                "wave": "tidepool_w16",
                "task": "T7",
                "before": "8885daa",
                "after": "9a9a9a9",
                "login": "tidepool-cli",
            }
        )

        # Assert
        self.assertEqual(
            event,
            TaskRebased(wave="tidepool_w16", task="T7", before="8885daa", after="9a9a9a9", login="tidepool-cli"),
        )
