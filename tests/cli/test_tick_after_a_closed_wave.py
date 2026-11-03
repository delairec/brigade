from tests.cli.test_tick_after_a_cancelled_wave import (
    BUILD_RUN_OF_THE_NEW_WAVE,
    NEW_WAVE_BRANCH,
    S3_IN_THE_NEW_WAVE,
    S3_PARKED_IN_THE_FIRST_WAVE,
)
from tests.cli.wave_tick_test_case import WAVE_BRANCH, LaunchingTickTestCase

FIRST_WAVE_CLOSED = (
    '{"schema_version": 1, "ts": "2026-10-13T10:30:00Z", "event": "wave.closed", "wave": "shop_w1", "pr": 31}\n'
)


class TickAfterTheClosureOfTheWaveOfAParkedTaskTest(LaunchingTickTestCase):
    def setUp(self):
        super().setUp()
        (self.state / "ledger" / "2026-10.jsonl").write_text(
            S3_PARKED_IN_THE_FIRST_WAVE + FIRST_WAVE_CLOSED + S3_IN_THE_NEW_WAVE
        )
        self.project.run_git(
            "worktree", "add", "--quiet", "-b", "task/M1-empty-cart/S3", str(self.worktree), WAVE_BRANCH
        )
        self.project.run_git("branch", NEW_WAVE_BRANCH, WAVE_BRANCH)

    def test_should_launch_the_build_run_of_the_new_wave_in_the_worktree_its_task_left_in_the_closed_wave(self):
        # Act
        self.run_tick("--once")
        self.wait_for_the_runs()

        # Assert
        self.assertEqual(self.read_events()[-1], BUILD_RUN_OF_THE_NEW_WAVE)
