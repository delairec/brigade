import unittest
from unittest import mock

from brigade.errors import BrigadeError
from brigade.tick.apply_actions import EXECUTORS, apply_actions

NO_RUNTIME_NEEDED = None


class LaunchRun:
    pass


class ApplyActionsTest(unittest.TestCase):
    def test_should_apply_an_empty_plan_as_no_action(self):
        # Arrange
        empty_plan = ()

        # Act
        actions_applied = apply_actions(empty_plan, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(actions_applied, 0)

    def test_should_refuse_an_action_it_has_no_executor_for(self):
        # Arrange
        plan = (LaunchRun(),)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            apply_actions(plan, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(str(refusal.exception), "the tick has no executor for the action LaunchRun")


class ApplyActionsWithAnExecutorTest(unittest.TestCase):
    def test_should_hand_each_action_to_the_executor_of_its_type(self):
        # Arrange
        applied = []
        action = LaunchRun()
        runtime = object()

        # Act
        with mock.patch.dict(EXECUTORS, {LaunchRun: lambda executed, given: applied.append((executed, given))}):
            actions_applied = apply_actions((action,), runtime)

        # Assert
        self.assertEqual((actions_applied, applied), (1, [(action, runtime)]))
