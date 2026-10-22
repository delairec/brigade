import unittest
from dataclasses import dataclass

from brigade.errors import BrigadeError, CommandFailed
from brigade.ledger.tick_action_failed import TickActionFailed
from brigade.tick.apply_actions import AppliedActions, apply_actions


@dataclass(frozen=True)
class LaunchRun:
    project: str
    wave: str
    task: str


@dataclass(frozen=True)
class LaunchStudy:
    study: str


class FailingExecutor:
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
        plan = (LaunchStudy(study="health"),)
        no_executors = {}
        failures = []

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            apply_actions(plan, no_executors, failures.append)

        # Assert
        self.assertEqual(str(refusal.exception), "the tick has no executor for the action LaunchStudy")

    def test_should_hand_each_action_to_the_executor_of_its_type_and_count_them(self):
        # Arrange
        first, second = LaunchStudy(study="health"), LaunchStudy(study="costs")
        executed = []
        failures = []

        # Act
        applied = apply_actions((first, second), {LaunchStudy: executed.append}, failures.append)

        # Assert
        self.assertEqual((applied, executed), (AppliedActions(applied=2, failed=()), [first, second]))


class ApplyActionsWithAFailingActionTest(unittest.TestCase):
    def test_should_apply_the_actions_that_follow_a_failed_one(self):
        # Arrange
        failing = LaunchRun(project="tidepool", wave="tidepool_w16", task="T7")
        following = LaunchRun(project="shop", wave="shop_w1", task="S3")
        executor = FailingExecutor(failing, CommandFailed(("git", "worktree", "add"), 128, "fatal: already exists"))
        failures = []

        # Act
        applied = apply_actions((failing, following), {LaunchRun: executor.execute}, failures.append)

        # Assert
        self.assertEqual((applied, executor.executed), (AppliedActions(applied=1, failed=(failing,)), [following]))

    def test_should_record_the_failed_action_its_project_wave_and_task_and_the_error(self):
        # Arrange
        failing = LaunchRun(project="tidepool", wave="tidepool_w16", task="T7")
        executor = FailingExecutor(failing, CommandFailed(("git", "worktree", "add"), 128, "fatal: already exists"))
        failures = []

        # Act
        apply_actions((failing,), {LaunchRun: executor.execute}, failures.append)

        # Assert
        self.assertEqual(
            failures,
            [
                TickActionFailed(
                    action="LaunchRun",
                    project="tidepool",
                    wave="tidepool_w16",
                    task="T7",
                    error="git worktree add exited 128: fatal: already exists",
                )
            ],
        )

    def test_should_record_no_project_wave_or_task_for_an_action_that_names_none(self):
        # Arrange
        failing = LaunchStudy(study="health")
        executor = FailingExecutor(failing, BrigadeError("the study health is not defined"))
        failures = []

        # Act
        apply_actions((failing,), {LaunchStudy: executor.execute}, failures.append)

        # Assert
        self.assertEqual(
            failures,
            [
                TickActionFailed(
                    action="LaunchStudy", project=None, wave=None, task=None, error="the study health is not defined"
                )
            ],
        )
