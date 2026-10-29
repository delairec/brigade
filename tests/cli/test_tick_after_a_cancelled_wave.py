from unittest.mock import ANY

from tests.cli.temporary_machine import CLONE_ENTRY_POINT
from tests.cli.wave_tick_test_case import WAVE_BRANCH, LaunchingTickTestCase
from tests.value_matchers import PatternMatcher

RUN_ID_PATTERN = r"^\d{8}T\d{6}Z-[0-9a-f]{6}$"
CONVENTIONAL_COMMITS_HOOK = (
    "#!/bin/sh\n"
    "head -n 1 \"$1\" | grep -qE '^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)"
    "(\\([a-zA-Z0-9._/-]+\\))?!?: .+'\n"
)
NEW_WAVE_BRANCH = "integration/M1-empty-cart-again"
S3_PARKED_IN_THE_FIRST_WAVE = (
    '{"schema_version": 2, "ts": "2026-10-13T09:00:00Z", "event": "wave.started", "wave": "shop_w1",'
    f' "project": "shop", "branch": "{WAVE_BRANCH}", "tasks": ["S3"]}}\n'
    '{"schema_version": 1, "ts": "2026-10-13T10:00:00Z", "event": "task.parked", "wave": "shop_w1", "task": "S3",'
    ' "reason": "run dead: 20261013T093000Z-a00001", "blockers": []}\n'
)
S3_IN_THE_NEW_WAVE = (
    '{"schema_version": 2, "ts": "2026-10-13T11:00:00Z", "event": "wave.started", "wave": "shop_w2",'
    f' "project": "shop", "branch": "{NEW_WAVE_BRANCH}", "tasks": ["S3"]}}\n'
)
BUILD_RUN_OF_THE_NEW_WAVE = {
    "schema_version": 2,
    "ts": ANY,
    "event": "run.finished",
    "run": PatternMatcher(RUN_ID_PATTERN),
    "segment": 1,
    "procedure": "build-task",
    "slot": "build",
    "role": "builder",
    "client": "fake",
    "project": "shop",
    "session": "fake-session",
    "main_steps": 12,
    "total_steps": None,
    "duration_ms": ANY,
    "usage": ANY,
    "outcome": "done",
    "error_class": None,
    "exit": 0,
    "wave": "shop_w2",
    "task": "S3",
    "nulls": ANY,
    "cost_usd": 0.42,
}


class TickAfterTheCancellationOfTheWaveOfAParkedTaskTestCase(LaunchingTickTestCase):
    def setUp(self):
        super().setUp()
        (self.state / "ledger" / "2026-10.jsonl").write_text(S3_PARKED_IN_THE_FIRST_WAVE)
        self.project.run_git(
            "worktree", "add", "--quiet", "-b", "task/M1-empty-cart/S3", str(self.worktree), WAVE_BRANCH
        )
        self.project.run_git("branch", NEW_WAVE_BRANCH, WAVE_BRANCH)

    def cancel_then_start_a_new_wave_then_tick(self) -> None:
        self.machine.run_brigade(
            CLONE_ENTRY_POINT, "wave", "cancel", "shop_w1", environment=self.describe_environment()
        )
        with (self.state / "ledger" / "2026-10.jsonl").open("a") as ledger:
            ledger.write(S3_IN_THE_NEW_WAVE)
        self.run_tick("--once")
        self.wait_for_the_runs()


class TickAfterTheCancellationOfTheWaveOfAParkedTaskTest(TickAfterTheCancellationOfTheWaveOfAParkedTaskTestCase):
    def test_should_launch_the_build_run_of_the_new_wave(self):
        # Act
        self.cancel_then_start_a_new_wave_then_tick()

        # Assert
        self.assertEqual(self.read_events()[-1], BUILD_RUN_OF_THE_NEW_WAVE)

    def test_should_run_the_build_in_the_worktree_path_of_the_task(self):
        # Act
        self.cancel_then_start_a_new_wave_then_tick()

        # Assert
        self.assertEqual(self.read_run_records()[-1]["worktree"], str(self.worktree))

    def test_should_put_the_worktree_on_the_task_branch_of_the_new_wave(self):
        # Act
        self.cancel_then_start_a_new_wave_then_tick()

        # Assert
        self.assertEqual(
            self.project.run_git("-C", str(self.worktree), "branch", "--show-current"),
            "task/M1-empty-cart-again/S3\n",
        )

    def test_should_keep_the_task_branch_of_the_cancelled_wave(self):
        # Act
        self.cancel_then_start_a_new_wave_then_tick()

        # Assert
        self.assertEqual(
            self.project.run_git("branch", "--list", "--format=%(refname:short)", "task/M1-empty-cart/S3"),
            "task/M1-empty-cart/S3\n",
        )


class TickAfterTheCancellationOfTheWaveOfAParkedTaskWithUncommittedChangesTest(
    TickAfterTheCancellationOfTheWaveOfAParkedTaskTestCase
):
    def setUp(self):
        super().setUp()
        (self.worktree / "notes.md").write_text("half of the work\n")

    def test_should_launch_the_build_run_of_the_new_wave(self):
        # Act
        self.cancel_then_start_a_new_wave_then_tick()

        # Assert
        self.assertEqual(self.read_events()[-1], BUILD_RUN_OF_THE_NEW_WAVE)

    def test_should_commit_the_uncommitted_file_on_the_task_branch_of_the_cancelled_wave(self):
        # Act
        self.cancel_then_start_a_new_wave_then_tick()

        # Assert
        self.assertEqual(
            self.project.run_git("show", "--name-only", "--format=", "task/M1-empty-cart/S3"), "notes.md\n"
        )


class TickAfterTheCancellationOfTheWaveOfAParkedTaskWithUncommittedChangesUnderAConventionalCommitsHookTest(
    TickAfterTheCancellationOfTheWaveOfAParkedTaskTestCase
):
    def setUp(self):
        super().setUp()
        (self.worktree / "notes.md").write_text("half of the work\n")
        hook = self.project.path / ".git" / "hooks" / "commit-msg"
        hook.write_text(CONVENTIONAL_COMMITS_HOOK)
        hook.chmod(0o755)

    def test_should_launch_the_build_run_of_the_new_wave(self):
        # Act
        self.cancel_then_start_a_new_wave_then_tick()

        # Assert
        self.assertEqual(self.read_events()[-1], BUILD_RUN_OF_THE_NEW_WAVE)
