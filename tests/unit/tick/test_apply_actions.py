import unittest

from brigade.errors import BrigadeError
from brigade.tick.apply_actions import apply_actions


class LaunchRun:
    pass


class ApplyActionsTest(unittest.TestCase):
    def test_should_apply_an_empty_plan_as_no_action(self):
        # Arrange
        empty_plan = ()

        # Act
        actions_applied = apply_actions(empty_plan)

        # Assert
        self.assertEqual(actions_applied, 0)

    def test_should_refuse_an_action_it_has_no_executor_for(self):
        # Arrange
        plan = (LaunchRun(),)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            apply_actions(plan)

        # Assert
        self.assertEqual(str(refusal.exception), "the tick has no executor for the action LaunchRun")
