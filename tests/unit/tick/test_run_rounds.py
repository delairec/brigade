import unittest
from datetime import UTC, datetime

from brigade.tick.build_snapshot import Snapshot
from brigade.tick.run_rounds import Rounds, RoundsOutcome, run_rounds

FIRST_SNAPSHOT = Snapshot(now=datetime(2026, 10, 6, 12, 0, tzinfo=UTC))
SECOND_SNAPSHOT = Snapshot(now=datetime(2026, 10, 6, 12, 1, tzinfo=UTC))
THIRD_SNAPSHOT = Snapshot(now=datetime(2026, 10, 6, 12, 2, tzinfo=UTC))
NO_ACTION = ()


class SnapshotBuilder:
    def __init__(self, snapshots: list):
        self.snapshots = iter(snapshots)

    def build(self) -> Snapshot:
        return next(self.snapshots)


class PlannerBySnapshot:
    def __init__(self, plans: dict):
        self.plans = plans
        self.snapshots_seen = []

    def plan(self, snapshot: Snapshot) -> tuple:
        self.snapshots_seen.append(snapshot)
        return self.plans[snapshot]


class RecordingExecutor:
    def __init__(self):
        self.plans_applied = []

    def apply(self, actions: tuple) -> int:
        self.plans_applied.append(actions)
        return len(actions)


def create_rounds(snapshots: list, planner: PlannerBySnapshot, executor: RecordingExecutor, cap: int = 10) -> Rounds:
    return Rounds(build_snapshot=SnapshotBuilder(snapshots).build, plan=planner.plan, apply=executor.apply, cap=cap)


class RunRoundsTest(unittest.TestCase):
    def test_should_stop_at_a_first_empty_plan_having_applied_nothing(self):
        # Arrange
        executor = RecordingExecutor()
        planner = PlannerBySnapshot({FIRST_SNAPSHOT: NO_ACTION})

        # Act
        outcome = run_rounds(create_rounds([FIRST_SNAPSHOT], planner, executor))

        # Assert
        self.assertEqual((outcome, executor.plans_applied), (RoundsOutcome(actions_applied=0, capped=False), []))

    def test_should_apply_each_plan_until_the_plan_is_empty(self):
        # Arrange
        executor = RecordingExecutor()
        planner = PlannerBySnapshot(
            {FIRST_SNAPSHOT: ("merge", "launch"), SECOND_SNAPSHOT: ("launch",), THIRD_SNAPSHOT: NO_ACTION}
        )

        # Act
        outcome = run_rounds(create_rounds([FIRST_SNAPSHOT, SECOND_SNAPSHOT, THIRD_SNAPSHOT], planner, executor))

        # Assert
        self.assertEqual(outcome, RoundsOutcome(actions_applied=3, capped=False))
        self.assertEqual(executor.plans_applied, [("merge", "launch"), ("launch",)])

    def test_should_plan_every_round_on_a_snapshot_built_afresh(self):
        # Arrange
        planner = PlannerBySnapshot(
            {FIRST_SNAPSHOT: ("merge",), SECOND_SNAPSHOT: ("launch",), THIRD_SNAPSHOT: NO_ACTION}
        )

        # Act
        run_rounds(create_rounds([FIRST_SNAPSHOT, SECOND_SNAPSHOT, THIRD_SNAPSHOT], planner, RecordingExecutor()))

        # Assert
        self.assertEqual(planner.snapshots_seen, [FIRST_SNAPSHOT, SECOND_SNAPSHOT, THIRD_SNAPSHOT])

    def test_should_stop_at_the_cap_when_the_plan_never_empties(self):
        # Arrange
        executor = RecordingExecutor()
        planner = PlannerBySnapshot(
            {FIRST_SNAPSHOT: ("launch",), SECOND_SNAPSHOT: ("launch",), THIRD_SNAPSHOT: ("launch",)}
        )

        # Act
        outcome = run_rounds(create_rounds([FIRST_SNAPSHOT, SECOND_SNAPSHOT, THIRD_SNAPSHOT], planner, executor, cap=3))

        # Assert
        self.assertEqual(outcome, RoundsOutcome(actions_applied=3, capped=True))
