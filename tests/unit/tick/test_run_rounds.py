import unittest
from datetime import datetime, timezone

from brigade.tick.build_snapshot import Snapshot
from brigade.tick.run_rounds import Rounds, RoundsOutcome, run_rounds

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)
SNAPSHOT = Snapshot(now=NOW)
NO_ACTION = ()


class ScriptedPlanner:
    def __init__(self, plans: list, plan_after_the_script: tuple = NO_ACTION):
        self.plans = plans
        self.plan_after_the_script = plan_after_the_script
        self.snapshots_seen = []

    def plan(self, snapshot: Snapshot) -> tuple:
        self.snapshots_seen.append(snapshot)
        if self.plans:
            return self.plans.pop(0)
        return self.plan_after_the_script


class RecordingExecutor:
    def __init__(self):
        self.plans_applied = []

    def apply(self, actions: tuple) -> int:
        self.plans_applied.append(actions)
        return len(actions)


def create_rounds(planner: ScriptedPlanner, executor: RecordingExecutor, cap: int = 10) -> Rounds:
    return Rounds(build_snapshot=lambda: SNAPSHOT, plan=planner.plan, apply=executor.apply, cap=cap)


class RunRounds(unittest.TestCase):
    def test_should_stop_at_a_first_empty_plan_having_applied_nothing(self):
        # Arrange
        executor = RecordingExecutor()

        # Act
        outcome = run_rounds(create_rounds(ScriptedPlanner([]), executor))

        # Assert
        self.assertEqual((outcome, executor.plans_applied), (RoundsOutcome(actions_applied=0, capped=False), []))

    def test_should_apply_each_plan_until_the_plan_is_empty(self):
        # Arrange
        executor = RecordingExecutor()
        planner = ScriptedPlanner([("merge", "launch"), ("launch",)])

        # Act
        outcome = run_rounds(create_rounds(planner, executor))

        # Assert
        self.assertEqual(outcome, RoundsOutcome(actions_applied=3, capped=False))
        self.assertEqual(executor.plans_applied, [("merge", "launch"), ("launch",)])

    def test_should_plan_every_round_on_a_snapshot_built_afresh(self):
        # Arrange
        planner = ScriptedPlanner([("merge",), ("launch",)])

        # Act
        run_rounds(create_rounds(planner, RecordingExecutor()))

        # Assert
        self.assertEqual(planner.snapshots_seen, [SNAPSHOT, SNAPSHOT, SNAPSHOT])

    def test_should_stop_at_the_cap_when_the_plan_never_empties(self):
        # Arrange
        executor = RecordingExecutor()
        planner = ScriptedPlanner([], plan_after_the_script=("launch",))

        # Act
        outcome = run_rounds(create_rounds(planner, executor, cap=3))

        # Assert
        self.assertEqual(outcome, RoundsOutcome(actions_applied=3, capped=True))
