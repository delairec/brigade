import unittest
from dataclasses import dataclass

from brigade.errors import BrigadeError
from brigade.tick.apply_actions import apply_actions

NO_RUNTIME_NEEDED = None


@dataclass(frozen=True)
class LaunchRun:
    task: str


class ApplyActions(unittest.TestCase):
    def test_should_apply_an_empty_plan_as_no_action(self):
        # Arrange
        empty_plan = ()

        # Act
        actions_applied = apply_actions(empty_plan, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(actions_applied, 0)

    def test_should_refuse_an_action_it_has_no_executor_for(self):
        # Arrange
        plan = (LaunchRun(task="B07"),)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            apply_actions(plan, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(str(refusal.exception), "the tick has no executor for the action LaunchRun")
