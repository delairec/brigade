import unittest
from datetime import UTC, datetime

from brigade.tick.build_snapshot import LiveRun, ProjectFacts, Snapshot, TaskFacts, WaveFacts
from brigade.tick.plan_launches import HeldTask, plan_launches
from brigade.waves.read_wave_pause import WavePause

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
NO_HALT = {}
ONE_SLOT = ProjectFacts(name="shop", slots=1)


def create_wave(tasks: tuple[TaskFacts, ...], states: dict, implemented: tuple[str, ...] = ()) -> WaveFacts:
    return WaveFacts(
        project="shop", wave="shop_w1", base="integration/cart", tasks=tasks, states=states, implemented=implemented
    )


class PlanLaunchesHeldTasksTest(unittest.TestCase):
    def test_should_hold_a_queued_task_the_slots_taken_by_the_launches_of_the_round_leave_out(self):
        # Arrange
        tasks = (TaskFacts(name="S9", branch="feature/S9-task"), TaskFacts(name="S3", branch="feature/S3-task"))
        snapshot = Snapshot(now=NOW, waves=(create_wave(tasks, {}),), projects=(ONE_SLOT,))

        # Act
        plan = plan_launches(snapshot, NO_HALT)

        # Assert
        self.assertEqual(
            plan.held,
            (HeldTask(project="shop", wave="shop_w1", task="S9", cause="no free build slot: 1 used of SLOTS 1"),),
        )

    def test_should_hold_each_queued_and_parked_task_of_a_wave_halted_in_the_round(self):
        # Arrange
        tasks = (
            TaskFacts(name="S3", branch="feature/S3-task"),
            TaskFacts(name="S4", branch="feature/S4-task", parked_reason="its run ended blocked"),
        )
        snapshot = Snapshot(now=NOW, waves=(create_wave(tasks, {"S4": "parked"}),), projects=(ONE_SLOT,))
        halts = {"shop_w1": WavePause(reason="the forge account is unavailable", resume_at=None)}

        # Act
        plan = plan_launches(snapshot, halts)

        # Assert
        self.assertEqual(
            plan.held,
            (
                HeldTask(
                    project="shop",
                    wave="shop_w1",
                    task="S3",
                    cause="wave shop_w1 parked: the forge account is unavailable;"
                    " it waits for brigade wave resume shop_w1",
                ),
                HeldTask(
                    project="shop",
                    wave="shop_w1",
                    task="S4",
                    cause="wave shop_w1 parked: the forge account is unavailable;"
                    " it waits for brigade wave resume shop_w1",
                ),
            ),
        )

    def test_should_hold_no_task_implemented_at_the_tree_running_or_relaunched(self):
        # Arrange
        project = ProjectFacts(
            name="shop",
            slots=1,
            live_runs=(
                LiveRun(run="20261006T110000Z-a1b2c3", slot="build", worktree="/w/S5", wave="shop_w1", task="S5"),
            ),
        )
        tasks = (
            TaskFacts(name="S3", branch="feature/S3-task"),
            TaskFacts(name="S4", branch="feature/S4-task", rebased_by_last_run=True),
            TaskFacts(name="S5", branch="feature/S5-task"),
        )
        wave = create_wave(tasks, {"S4": "running", "S5": "running"}, implemented=("S3",))
        snapshot = Snapshot(now=NOW, waves=(wave,), projects=(project,))

        # Act
        plan = plan_launches(snapshot, NO_HALT)

        # Assert
        self.assertEqual(plan.held, ())


if __name__ == "__main__":
    unittest.main()
