from tests.cli.test_tick_after_a_cancelled_wave import (
    BUILD_RUN_OF_THE_NEW_WAVE,
    S3_IN_THE_NEW_WAVE,
    S3_PARKED_IN_THE_FIRST_WAVE,
)
from tests.cli.wave_tick_test_case import MILESTONE_BRANCH, MILESTONE_BRANCH_CUT, TASK_BRANCH, LaunchingTickTestCase

FIRST_WAVE_CLOSED = '{"schema_version": 1, "ts": "2026-10-13T10:30:00Z", "event": "wave.closed", "wave": "shop_w1"}\n'


class TickAfterTheClosureOfTheWaveOfAParkedTaskTest(LaunchingTickTestCase):
    def setUp(self):
        super().setUp()
        (self.state / "ledger" / "2026-10.jsonl").write_text(
            MILESTONE_BRANCH_CUT + S3_PARKED_IN_THE_FIRST_WAVE + FIRST_WAVE_CLOSED + S3_IN_THE_NEW_WAVE
        )
        self.project.run_git("worktree", "add", "--quiet", "-b", TASK_BRANCH, str(self.worktree), MILESTONE_BRANCH)

    def test_should_launch_the_build_run_of_the_new_wave_in_the_worktree_its_task_left_in_the_closed_wave(self):
        # Act
        self.run_tick("--once")
        self.wait_for_the_runs()

        # Assert
        self.assertEqual(self.read_events()[-1], BUILD_RUN_OF_THE_NEW_WAVE)
