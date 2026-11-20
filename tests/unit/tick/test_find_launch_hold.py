import unittest
from datetime import UTC, datetime

from brigade.tick.build_snapshot import TaskFacts, WaveFacts
from brigade.tick.find_launch_hold import LaunchRound, find_launch_hold
from brigade.waves.read_wave_pause import WavePause

QUEUED = "queued"
PARKED = "parked"
MERGED = "merged"
RUNNING = "running"
BLOCKED_WAVE = WavePause(reason="the quota of claude is spent", resume_at=datetime(2026, 10, 6, 13, 0, tzinfo=UTC))
PARKED_WAVE = WavePause(reason="the login of its AI client is lost", resume_at=None)
NO_HALT = None
FREE_SLOT = LaunchRound(halt=NO_HALT, used_slots=1, slots=2)
NO_FREE_SLOT = LaunchRound(halt=NO_HALT, used_slots=2, slots=2)
NOTHING_IMPLEMENTED = ()

ALONE = TaskFacts(name="S3", branch="feature/S3-task")
PARKED_ON_ITS_RUN = TaskFacts(name="S3", branch="feature/S3-task", parked_reason="its run ended blocked")
AFTER_S2 = TaskFacts(name="S3", branch="feature/S3-task", after=("S1", "S2"))
BLOCKED_BY_A_QUESTION = TaskFacts(name="S3", branch="feature/S3-task", blocked_by=("OPEN_QUESTION.Undecided",))
AFTER_S2_AND_BLOCKED = TaskFacts(
    name="S3", branch="feature/S3-task", after=("S2",), blocked_by=("OPEN_QUESTION.Undecided",)
)


def create_wave(task: TaskFacts, states: dict, implemented: tuple[str, ...]) -> WaveFacts:
    return WaveFacts(project="shop", wave="shop_w1", tasks=(task,), states=states, implemented=implemented)


class FindLaunchHoldTest(unittest.TestCase):
    def test_should_name_the_first_cause_that_holds_a_task(self):
        for case, task, states, implemented, launch_round, expected in [
            (
                "a blocked wave",
                PARKED_ON_ITS_RUN,
                {"S3": PARKED},
                NOTHING_IMPLEMENTED,
                LaunchRound(halt=BLOCKED_WAVE, used_slots=2, slots=2),
                "wave shop_w1 blocked until 2026-10-06T13:00:00Z: the quota of claude is spent",
            ),
            (
                "a parked wave",
                AFTER_S2,
                {"S3": QUEUED},
                NOTHING_IMPLEMENTED,
                LaunchRound(halt=PARKED_WAVE, used_slots=1, slots=2),
                "wave shop_w1 parked: the login of its AI client is lost; it waits for brigade wave resume shop_w1",
            ),
            (
                "a parked task",
                PARKED_ON_ITS_RUN,
                {"S3": PARKED},
                NOTHING_IMPLEMENTED,
                NO_FREE_SLOT,
                "parked: its run ended blocked",
            ),
            (
                "an AFTER neither merged nor implemented",
                AFTER_S2,
                {"S1": MERGED, "S2": RUNNING, "S3": QUEUED},
                NOTHING_IMPLEMENTED,
                NO_FREE_SLOT,
                "after S2",
            ),
            (
                "a live blocker",
                BLOCKED_BY_A_QUESTION,
                {"S3": QUEUED},
                (),
                NO_FREE_SLOT,
                "blocked by OPEN_QUESTION.Undecided",
            ),
            (
                "no free build slot",
                ALONE,
                {"S3": QUEUED},
                NOTHING_IMPLEMENTED,
                NO_FREE_SLOT,
                "no free build slot: 2 used of SLOTS 2",
            ),
            ("an AFTER before a live blocker", AFTER_S2_AND_BLOCKED, {"S3": QUEUED}, (), FREE_SLOT, "after S2"),
            ("an AFTER implemented at the tree", AFTER_S2, {"S1": MERGED, "S3": QUEUED}, ("S2",), FREE_SLOT, None),
            ("a startable task", ALONE, {}, NOTHING_IMPLEMENTED, FREE_SLOT, None),
            ("a running task relaunched", AFTER_S2_AND_BLOCKED, {"S3": RUNNING}, (), FREE_SLOT, None),
            (
                "a running task relaunched without a slot",
                AFTER_S2,
                {"S3": RUNNING},
                (),
                NO_FREE_SLOT,
                "no free build slot: 2 used of SLOTS 2",
            ),
        ]:
            with self.subTest(case=case):
                # Arrange
                wave = create_wave(task, states, implemented)

                # Act
                hold = find_launch_hold(task, wave, launch_round)

                # Assert
                self.assertEqual(hold, expected)


if __name__ == "__main__":
    unittest.main()
