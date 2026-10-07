import unittest

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


class ApplyActionsWithARegisteredExecutorTest(unittest.TestCase):
    def setUp(self):
        self.applied = []
        EXECUTORS[LaunchRun] = lambda action, runtime: self.applied.append((action, runtime))
        self.addCleanup(EXECUTORS.pop, LaunchRun, None)

    def test_should_call_the_executor_of_each_action(self):
        # Arrange
        action = LaunchRun()
        plan = (action,)

        # Act
        actions_applied = apply_actions(plan, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(actions_applied, 1)
        self.assertEqual(self.applied, [(action, NO_RUNTIME_NEEDED)])
