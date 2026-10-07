import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import ANY

from tests.cli.run_test_case import COUNTING_CLIENT, DONE_RESULT, RunTestCase
from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine

EXECUTABLES = Path(__file__).resolve().parent / "fixtures" / "executables"
SYSTEMD_USER_MANAGER = str(EXECUTABLES / "systemd-user-manager")
TICK_TRAIL_PATTERN = r"^\d{8}T\d{6}Z\.jsonl$"
QUICK_PROCEDURE = "---\ncapabilities: read, write, shell\nbudget: 1\n---\nAnswer at once.\n"


def read_trail(path: Path) -> list:
    return [json.loads(line) for line in path.read_text().splitlines()]


class BrigadeRunTrailTest(RunTestCase):
    def run_in_workspace(self, *options: str):
        return self.run_brigade("run", str(self.procedure), "--cwd", str(self.workspace), *options)

    def locate_only_run(self) -> Path:
        [run_directory] = self.runs.iterdir()
        return run_directory

    def test_should_record_the_subprocess_whose_exit_code_is_refused(self):
        # Arrange
        self.configure_fake('features = "step_count"\n')
        self.record("explorer", DONE_RESULT)

        # Act
        completed = self.run_in_workspace("--slot", "explore")

        # Assert
        self.assertEqual(completed.returncode, 1, completed.stdout)
        run_directory = self.locate_only_run()
        self.assertEqual(
            read_trail(run_directory / "processes.jsonl"),
            [
                {
                    "schema_version": 1,
                    "argv": ["git", "worktree", "add", "--quiet", "--detach", str(run_directory / "worktree"), "HEAD"],
                    "cwd": str(self.workspace),
                    "exit": 128,
                    "duration_ms": ANY,
                    "outcome": "exited",
                }
            ],
        )

    def test_should_record_the_client_segment_after_its_wait(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)

        # Act
        completed = self.run_in_workspace("--slot", "build", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            read_trail(self.runs / json.loads(completed.stdout)["run"] / "processes.jsonl"),
            [
                {
                    "schema_version": 1,
                    "argv": ["cat", "--", str(self.recordings / "builder.json")],
                    "cwd": str(self.workspace),
                    "exit": 0,
                    "duration_ms": ANY,
                    "outcome": "exited",
                }
            ],
        )

    def test_should_record_a_client_segment_cut_at_its_wall_limit(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT + 'delay = "10"\n', keys="seconds_per_step = 0.2\n")
        self.record("builder", DONE_RESULT)
        quick = self.procedure.with_name("quick.md")
        quick.write_text(QUICK_PROCEDURE)

        # Act
        completed = self.run_brigade("run", str(quick), "--slot", "build", "--cwd", str(self.workspace), "--json")

        # Assert
        self.assertEqual(completed.returncode, 1, completed.stderr)
        [record] = read_trail(self.runs / json.loads(completed.stdout)["run"] / "processes.jsonl")
        self.assertEqual((record["outcome"], record["exit"]), ("cut", None))

    def test_should_render_the_record_on_stderr_under_verbose(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)

        # Act
        completed = self.run_in_workspace("--slot", "build", "--verbose")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertRegex(
            completed.stderr, rf"^brigade run: ran cat -- {self.recordings}/builder\.json, exit 0 in \d+ ms\n$"
        )


class BrigadeRunDetachedTrailTest(RunTestCase):
    def setUp(self):
        super().setUp()
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)

    def test_should_print_the_spawned_line_and_hand_no_verbose_to_the_process_it_re_executes(self):
        # Act
        completed = self.run_brigade(
            "run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), "--detach", "--verbose"
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        run_directory = self.runs / completed.stdout.strip()
        pid = int((run_directory / "pid").read_text())
        self.wait_for_file(run_directory / "result.json")
        self.wait_for_exit(pid)
        self.assertRegex(
            completed.stderr,
            rf"^brigade run: ran {sys.executable} {CLONE_ENTRY_POINT} run .* --run-id {run_directory.name}, spawned pid {pid}\n$",
        )
        self.assertEqual(
            (run_directory / "brigade.log").read_text(),
            f"run {run_directory.name}: deliver as builder (build) done after 1 segment\n",
        )

    def test_should_record_the_spawned_run_and_the_records_of_the_process_it_re_executes(self):
        # Act
        completed = self.run_brigade(
            "run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), "--detach"
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        run_directory = self.runs / completed.stdout.strip()
        pid = int((run_directory / "pid").read_text())
        self.wait_for_file(run_directory / "result.json")
        self.wait_for_exit(pid)
        spawned, segment = read_trail(run_directory / "processes.jsonl")
        self.assertEqual(
            spawned,
            {
                "schema_version": 1,
                "argv": ANY,
                "cwd": str(self.workspace),
                "exit": None,
                "duration_ms": None,
                "outcome": "spawned",
                "pid": pid,
            },
        )
        self.assertEqual(segment["argv"], ["cat", "--", str(self.recordings / "builder.json")])


class TrailTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.machine = TemporaryMachine(Path(self.root.name).resolve())
        self.state = self.machine.state_home / "brigade"
        self.ticks = self.state / "ticks"
        self.commands = self.state / "commands"

    def tearDown(self):
        self.root.cleanup()

    def run_brigade(self, *arguments: str):
        return self.machine.run_brigade(CLONE_ENTRY_POINT, *arguments)

    def write_trails(self, *paths: Path) -> None:
        for path in paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("")


class BrigadeTickTrailTest(TrailTestCase):
    def test_should_write_the_trail_of_the_tick(self):
        # Act
        completed = self.run_brigade("tick", "--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        [trail] = self.ticks.iterdir()
        self.assertRegex(trail.name, TICK_TRAIL_PATTERN)

    def test_should_write_no_tick_trail_on_a_dry_run(self):
        # Act
        completed = self.run_brigade("tick", "--dry-run")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertFalse(self.ticks.exists())

    def test_should_remove_the_trails_older_than_seven_days_by_default(self):
        # Arrange
        old_tick = self.ticks / "20000101T000000Z.jsonl"
        old_command = self.commands / "20000101T000000Z-doctor.jsonl"
        future_command = self.commands / "29991231T000000Z-doctor.jsonl"
        self.write_trails(old_tick, old_command, future_command)

        # Act
        completed = self.run_brigade("tick", "--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            (old_tick.exists(), old_command.exists(), future_command.exists()),
            (False, False, True),
        )

    def test_should_keep_the_trails_younger_than_the_trail_days_of_config_toml(self):
        # Arrange
        self.machine.write_configuration("trail_days = 100000\n")
        old_tick = self.ticks / "20000101T000000Z.jsonl"
        self.write_trails(old_tick)

        # Act
        completed = self.run_brigade("tick", "--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(old_tick.exists())


class BrigadeCommandTrailTest(TrailTestCase):
    def setUp(self):
        super().setUp()
        self.environment = {**self.machine.describe_environment(), "PATH": SYSTEMD_USER_MANAGER}

    def run_status(self, *options: str):
        return self.machine.run_brigade(
            CLONE_ENTRY_POINT, "scheduler", "status", *options, environment=self.environment
        )

    def test_should_write_the_trail_of_the_command_named_after_it(self):
        # Act
        completed = self.run_status("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        [trail] = self.commands.glob("*-scheduler-status.jsonl")
        self.assertEqual(
            read_trail(trail),
            [
                {
                    "schema_version": 1,
                    "argv": ["crontab", "-l"],
                    "cwd": "/",
                    "exit": None,
                    "duration_ms": ANY,
                    "outcome": "not_found",
                }
            ],
        )

    def test_should_render_each_record_on_stderr_and_leave_stdout_unchanged_under_verbose(self):
        # Arrange
        quiet = self.run_status("--json")

        # Act
        verbose = self.run_status("--json", "--verbose")

        # Assert
        self.assertEqual(
            (verbose.returncode, verbose.stdout, verbose.stderr),
            (0, quiet.stdout, "brigade scheduler status: ran crontab -l, not on PATH\n"),
        )

    def test_should_render_each_record_on_stderr_under_a_verbose_given_before_the_command(self):
        # Act
        completed = self.machine.run_brigade(
            CLONE_ENTRY_POINT, "--verbose", "scheduler", "status", environment=self.environment
        )

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr),
            (0, "brigade scheduler status: ran crontab -l, not on PATH\n"),
        )

    def test_should_print_no_record_on_stderr_without_verbose(self):
        # Act
        completed = self.run_status("--json")

        # Assert
        self.assertEqual((completed.returncode, completed.stderr), (0, ""))
