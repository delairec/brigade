import unittest

from brigade.ledger.task_parked import TaskParked
from brigade.ledger.task_state import TaskState
from brigade.waves.read_task_state import read_task_state


class ReadTaskStateTest(unittest.TestCase):
    def test_should_read_the_state_an_event_leaves_the_task_in(self):
        # Arrange
        rows = [
            (
                "parked by its blockers",
                TaskParked(wave="shop_w1", task="S3", reason="blocked", blockers=("OPEN_QUESTION.Undecided",)),
                "parked",
            ),
            ("moved to a state", TaskState(wave="shop_w1", task="S3", state="pr_open"), "pr_open"),
        ]
        for case, event, expected_state in rows:
            with self.subTest(case=case):
                # Act
                state = read_task_state(event)

                # Assert
                self.assertEqual(state, expected_state)
