import unittest
from datetime import UTC, datetime

from brigade.tick.apply_actions import AppliedActions
from brigade.tick.build_snapshot import Snapshot
from brigade.tick.run_cycles import Cycles, CyclesOutcome, run_cycles

FIRST_SNAPSHOT = Snapshot(now=datetime(2026, 10, 6, 12, 0, tzinfo=UTC))
SECOND_SNAPSHOT = Snapshot(now=datetime(2026, 10, 6, 12, 1, tzinfo=UTC))
THIRD_SNAPSHOT = Snapshot(now=datetime(2026, 10, 6, 12, 2, tzinfo=UTC))
NO_ACTION = ()


class SnapshotBuilderDouble:
    def __init__(self, snapshots: list):
        self.snapshots = iter(snapshots)

    def build(self) -> Snapshot:
        return next(self.snapshots)


class DeciderBySnapshotDouble:
    def __init__(self, decisions: dict):
        self.decisions = decisions
        self.snapshots_seen = []

    def decide(self, snapshot: Snapshot) -> tuple:
        self.snapshots_seen.append(snapshot)
        return self.decisions[snapshot]


class RecordingExecutorDouble:
    def __init__(self):
        self.decisions_applied = []

    def apply(self, actions: tuple) -> AppliedActions:
        self.decisions_applied.append(actions)
        return AppliedActions(applied=len(actions), failed=())


class ExecutorFailingOnDouble:
    def __init__(self, failing: str):
        self.failing = failing
        self.decisions_applied = []

    def apply(self, actions: tuple) -> AppliedActions:
        self.decisions_applied.append(actions)
        failed = tuple(action for action in actions if action == self.failing)
        return AppliedActions(applied=len(actions) - len(failed), failed=failed)


def create_cycles(snapshots: list, decider: DeciderBySnapshotDouble, executor, cap: int = 10) -> Cycles:
    return Cycles(
        build_snapshot=SnapshotBuilderDouble(snapshots).build, decide=decider.decide, apply=executor.apply, cap=cap
    )


class RunCyclesTest(unittest.TestCase):
    def test_should_stop_at_a_first_cycle_deciding_nothing_having_applied_nothing(self):
        # Arrange
        executor = RecordingExecutorDouble()
        decider = DeciderBySnapshotDouble({FIRST_SNAPSHOT: NO_ACTION})

        # Act
        outcome = run_cycles(create_cycles([FIRST_SNAPSHOT], decider, executor))

        # Assert
        self.assertEqual(outcome, CyclesOutcome(actions_applied=0, actions_failed=0))
        self.assertEqual(executor.decisions_applied, [])

    def test_should_apply_the_decisions_of_each_cycle_until_none_is_left(self):
        # Arrange
        executor = RecordingExecutorDouble()
        decider = DeciderBySnapshotDouble(
            {FIRST_SNAPSHOT: ("merge", "launch"), SECOND_SNAPSHOT: ("launch",), THIRD_SNAPSHOT: NO_ACTION}
        )

        # Act
        outcome = run_cycles(create_cycles([FIRST_SNAPSHOT, SECOND_SNAPSHOT, THIRD_SNAPSHOT], decider, executor))

        # Assert
        self.assertEqual(outcome, CyclesOutcome(actions_applied=3, actions_failed=0))
        self.assertEqual(executor.decisions_applied, [("merge", "launch"), ("launch",)])

    def test_should_decide_every_cycle_on_a_snapshot_built_afresh(self):
        # Arrange
        decider = DeciderBySnapshotDouble(
            {FIRST_SNAPSHOT: ("merge",), SECOND_SNAPSHOT: ("launch",), THIRD_SNAPSHOT: NO_ACTION}
        )

        # Act
        run_cycles(create_cycles([FIRST_SNAPSHOT, SECOND_SNAPSHOT, THIRD_SNAPSHOT], decider, RecordingExecutorDouble()))

        # Assert
        self.assertEqual(decider.snapshots_seen, [FIRST_SNAPSHOT, SECOND_SNAPSHOT, THIRD_SNAPSHOT])

    def test_should_stop_at_the_cap_when_the_decisions_never_run_out(self):
        # Arrange
        executor = RecordingExecutorDouble()
        decider = DeciderBySnapshotDouble(
            {FIRST_SNAPSHOT: ("launch",), SECOND_SNAPSHOT: ("launch",), THIRD_SNAPSHOT: ("launch",)}
        )

        # Act
        outcome = run_cycles(create_cycles([FIRST_SNAPSHOT, SECOND_SNAPSHOT, THIRD_SNAPSHOT], decider, executor, cap=3))

        # Assert
        self.assertEqual(outcome, CyclesOutcome(actions_applied=3, actions_failed=0))


class RunCyclesWithAFailedActionTest(unittest.TestCase):
    def test_should_count_the_failed_actions_apart_from_the_applied_ones(self):
        # Arrange
        executor = ExecutorFailingOnDouble("merge")
        decider = DeciderBySnapshotDouble({FIRST_SNAPSHOT: ("merge", "launch"), SECOND_SNAPSHOT: NO_ACTION})

        # Act
        outcome = run_cycles(create_cycles([FIRST_SNAPSHOT, SECOND_SNAPSHOT], decider, executor))

        # Assert
        self.assertEqual(outcome, CyclesOutcome(actions_applied=1, actions_failed=1))

    def test_should_not_apply_again_in_the_same_tick_an_action_that_failed(self):
        # Arrange
        executor = ExecutorFailingOnDouble("merge")
        decider = DeciderBySnapshotDouble(
            {FIRST_SNAPSHOT: ("merge", "launch"), SECOND_SNAPSHOT: ("merge", "report"), THIRD_SNAPSHOT: ("merge",)}
        )

        # Act
        outcome = run_cycles(create_cycles([FIRST_SNAPSHOT, SECOND_SNAPSHOT, THIRD_SNAPSHOT], decider, executor))

        # Assert
        self.assertEqual(outcome, CyclesOutcome(actions_applied=2, actions_failed=1))
        self.assertEqual(executor.decisions_applied, [("merge", "launch"), ("report",)])
