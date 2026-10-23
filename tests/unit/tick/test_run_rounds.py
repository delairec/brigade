import unittest
from datetime import UTC, datetime

from brigade.tick.apply_actions import AppliedActions
from brigade.tick.build_snapshot import Snapshot
from brigade.tick.run_rounds import Rounds, RoundsOutcome, run_rounds

FIRST_SNAPSHOT = Snapshot(now=datetime(2026, 10, 6, 12, 0, tzinfo=UTC))
SECOND_SNAPSHOT = Snapshot(now=datetime(2026, 10, 6, 12, 1, tzinfo=UTC))
THIRD_SNAPSHOT = Snapshot(now=datetime(2026, 10, 6, 12, 2, tzinfo=UTC))
NO_ACTION = ()


class SnapshotBuilderDouble:
    def __init__(self, snapshots: list):
        self.snapshots = iter(snapshots)

    def build(self) -> Snapshot:
        return next(self.snapshots)


class PlannerBySnapshotDouble:
    def __init__(self, plans: dict):
        self.plans = plans
        self.snapshots_seen = []

    def plan(self, snapshot: Snapshot) -> tuple:
        self.snapshots_seen.append(snapshot)
        return self.plans[snapshot]


class RecordingExecutorDouble:
    def __init__(self):
        self.plans_applied = []

    def apply(self, actions: tuple) -> AppliedActions:
        self.plans_applied.append(actions)
        return AppliedActions(applied=len(actions), failed=())


class ExecutorFailingOnDouble:
    def __init__(self, failing: str):
        self.failing = failing
        self.plans_applied = []

    def apply(self, actions: tuple) -> AppliedActions:
        self.plans_applied.append(actions)
        failed = tuple(action for action in actions if action == self.failing)
        return AppliedActions(applied=len(actions) - len(failed), failed=failed)


def create_rounds(snapshots: list, planner: PlannerBySnapshotDouble, executor, cap: int = 10) -> Rounds:
    return Rounds(
        build_snapshot=SnapshotBuilderDouble(snapshots).build, plan=planner.plan, apply=executor.apply, cap=cap
    )


class RunRoundsTest(unittest.TestCase):
    def test_should_stop_at_a_first_empty_plan_having_applied_nothing(self):
        # Arrange
        executor = RecordingExecutorDouble()
        planner = PlannerBySnapshotDouble({FIRST_SNAPSHOT: NO_ACTION})

        # Act
        outcome = run_rounds(create_rounds([FIRST_SNAPSHOT], planner, executor))

        # Assert
        self.assertEqual(outcome, RoundsOutcome(actions_applied=0, actions_failed=0))
        self.assertEqual(executor.plans_applied, [])

    def test_should_apply_each_plan_until_the_plan_is_empty(self):
        # Arrange
        executor = RecordingExecutorDouble()
        planner = PlannerBySnapshotDouble(
            {FIRST_SNAPSHOT: ("merge", "launch"), SECOND_SNAPSHOT: ("launch",), THIRD_SNAPSHOT: NO_ACTION}
        )

        # Act
        outcome = run_rounds(create_rounds([FIRST_SNAPSHOT, SECOND_SNAPSHOT, THIRD_SNAPSHOT], planner, executor))

        # Assert
        self.assertEqual(outcome, RoundsOutcome(actions_applied=3, actions_failed=0))
        self.assertEqual(executor.plans_applied, [("merge", "launch"), ("launch",)])

    def test_should_plan_every_round_on_a_snapshot_built_afresh(self):
        # Arrange
        planner = PlannerBySnapshotDouble(
            {FIRST_SNAPSHOT: ("merge",), SECOND_SNAPSHOT: ("launch",), THIRD_SNAPSHOT: NO_ACTION}
        )

        # Act
        run_rounds(create_rounds([FIRST_SNAPSHOT, SECOND_SNAPSHOT, THIRD_SNAPSHOT], planner, RecordingExecutorDouble()))

        # Assert
        self.assertEqual(planner.snapshots_seen, [FIRST_SNAPSHOT, SECOND_SNAPSHOT, THIRD_SNAPSHOT])

    def test_should_stop_at_the_cap_when_the_plan_never_empties(self):
        # Arrange
        executor = RecordingExecutorDouble()
        planner = PlannerBySnapshotDouble(
            {FIRST_SNAPSHOT: ("launch",), SECOND_SNAPSHOT: ("launch",), THIRD_SNAPSHOT: ("launch",)}
        )

        # Act
        outcome = run_rounds(create_rounds([FIRST_SNAPSHOT, SECOND_SNAPSHOT, THIRD_SNAPSHOT], planner, executor, cap=3))

        # Assert
        self.assertEqual(outcome, RoundsOutcome(actions_applied=3, actions_failed=0))


class RunRoundsWithAFailedActionTest(unittest.TestCase):
    def test_should_count_the_failed_actions_apart_from_the_applied_ones(self):
        # Arrange
        executor = ExecutorFailingOnDouble("merge")
        planner = PlannerBySnapshotDouble({FIRST_SNAPSHOT: ("merge", "launch"), SECOND_SNAPSHOT: NO_ACTION})

        # Act
        outcome = run_rounds(create_rounds([FIRST_SNAPSHOT, SECOND_SNAPSHOT], planner, executor))

        # Assert
        self.assertEqual(outcome, RoundsOutcome(actions_applied=1, actions_failed=1))

    def test_should_not_apply_again_in_the_same_tick_an_action_that_failed(self):
        # Arrange
        executor = ExecutorFailingOnDouble("merge")
        planner = PlannerBySnapshotDouble(
            {FIRST_SNAPSHOT: ("merge", "launch"), SECOND_SNAPSHOT: ("merge", "report"), THIRD_SNAPSHOT: ("merge",)}
        )

        # Act
        outcome = run_rounds(create_rounds([FIRST_SNAPSHOT, SECOND_SNAPSHOT, THIRD_SNAPSHOT], planner, executor))

        # Assert
        self.assertEqual(outcome, RoundsOutcome(actions_applied=2, actions_failed=1))
        self.assertEqual(executor.plans_applied, [("merge", "launch"), ("report",)])
