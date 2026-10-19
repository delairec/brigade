import unittest

from brigade.errors import BrigadeError
from brigade.tick.apply_actions import apply_actions


class LaunchRun:
    pass


class ApplyActionsTest(unittest.TestCase):
    def test_should_apply_an_empty_plan_as_no_action(self):
        # Arrange
        empty_plan = ()
        no_executors = {}

        # Act
        actions_applied = apply_actions(empty_plan, no_executors)

        # Assert
        self.assertEqual(actions_applied, 0)

    def test_should_refuse_an_action_it_has_no_executor_for(self):
        # Arrange
        plan = (LaunchRun(),)
        no_executors = {}

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            apply_actions(plan, no_executors)

        # Assert
        self.assertEqual(str(refusal.exception), "the tick has no executor for the action LaunchRun")

    def test_should_hand_each_action_to_the_executor_of_its_type_and_count_them(self):
        # Arrange
        first, second = LaunchRun(), LaunchRun()
        executed = []

        # Act
        actions_applied = apply_actions((first, second), {LaunchRun: executed.append})

        # Assert
        self.assertEqual((actions_applied, executed), (2, [first, second]))
