import unittest
from dataclasses import dataclass

from brigade.errors import BrigadeError, CommandFailed
from brigade.ledger.tick_action_failed import TickActionFailed
from brigade.tick.apply_actions import AppliedActions, apply_actions


@dataclass(frozen=True)
class LaunchRunDouble:
    project: str
    wave: str
    task: str


@dataclass(frozen=True)
class LaunchStudyDouble:
    study: str


class FailingExecutorDouble:
    def __init__(self, failing: object, error: BrigadeError):
        self.failing = failing
        self.error = error
        self.executed = []

    def execute(self, action: object) -> None:
        if action == self.failing:
            raise self.error
        self.executed.append(action)


class ApplyActionsTest(unittest.TestCase):
    def test_should_apply_an_empty_plan_as_no_action(self):
        # Arrange
        empty_plan = ()
        no_executors = {}
        failures = []

        # Act
        applied = apply_actions(empty_plan, no_executors, failures.append)

        # Assert
        self.assertEqual(applied, AppliedActions(applied=0, failed=()))

    def test_should_refuse_an_action_it_has_no_executor_for(self):
        # Arrange
        plan = (LaunchStudyDouble(study="health"),)
        no_executors = {}
        failures = []

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            apply_actions(plan, no_executors, failures.append)

        # Assert
        self.assertEqual(str(refusal.exception), "the tick has no executor for the action LaunchStudyDouble")

    def test_should_hand_each_action_to_the_executor_of_its_type_and_count_them(self):
        # Arrange
        first, second = LaunchStudyDouble(study="health"), LaunchStudyDouble(study="costs")
        executed = []
        failures = []

        # Act
        applied = apply_actions((first, second), {LaunchStudyDouble: executed.append}, failures.append)

        # Assert
        self.assertEqual(applied, AppliedActions(applied=2, failed=()))
        self.assertEqual(executed, [first, second])


class ApplyActionsWithAFailingActionTest(unittest.TestCase):
    def test_should_apply_the_actions_that_follow_a_failed_one(self):
        # Arrange
        failing = LaunchRunDouble(project="tidepool", wave="tidepool_w16", task="T7")
        following = LaunchRunDouble(project="shop", wave="shop_w1", task="S3")
        executor = FailingExecutorDouble(
            failing, CommandFailed(("git", "worktree", "add"), 128, "fatal: already exists")
        )
        failures = []

        # Act
        applied = apply_actions((failing, following), {LaunchRunDouble: executor.execute}, failures.append)

        # Assert
        self.assertEqual(applied, AppliedActions(applied=1, failed=(failing,)))
        self.assertEqual(executor.executed, [following])

    def test_should_record_the_failed_action_its_project_wave_and_task_and_the_error(self):
        # Arrange
        failing = LaunchRunDouble(project="tidepool", wave="tidepool_w16", task="T7")
        executor = FailingExecutorDouble(
            failing, CommandFailed(("git", "worktree", "add"), 128, "fatal: already exists")
        )
        failures = []

        # Act
        apply_actions((failing,), {LaunchRunDouble: executor.execute}, failures.append)

        # Assert
        self.assertEqual(
            failures,
            [
                TickActionFailed(
                    action="LaunchRunDouble",
                    project="tidepool",
                    wave="tidepool_w16",
                    task="T7",
                    error="git worktree add exited 128: fatal: already exists",
                )
            ],
        )

    def test_should_record_no_project_wave_or_task_for_an_action_that_names_none(self):
        # Arrange
        failing = LaunchStudyDouble(study="health")
        executor = FailingExecutorDouble(failing, BrigadeError("the study health is not defined"))
        failures = []

        # Act
        apply_actions((failing,), {LaunchStudyDouble: executor.execute}, failures.append)

        # Assert
        self.assertEqual(
            failures,
            [
                TickActionFailed(
                    action="LaunchStudyDouble",
                    project=None,
                    wave=None,
                    task=None,
                    error="the study health is not defined",
                )
            ],
        )
