import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import ANY

from tests.cli.run_test_case import COUNTING_CLIENT, DONE_RESULT, RunTestCase
from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine

EXECUTABLES = Path(__file__).resolve().parent / "fixtures" / "executables"
SYSTEMD_USER_MANAGER = str(EXECUTABLES / "systemd-user-manager")
TICK_TRAIL_PATTERN = r"^\d{8}T\d{6}Z\.jsonl$"


def read_trail(path: Path) -> list:
    return [json.loads(line) for line in path.read_text().splitlines()]


class BrigadeRunTrailTest(RunTestCase):
    def run_in_workspace(self, *options: str):
        return self.run_brigade("run", str(self.procedure), "--cwd", str(self.workspace), *options)

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


class TrailTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.machine = TemporaryMachine(Path(self.root.name).resolve())
        self.state = self.machine.state_home / "brigade"
        self.ticks = self.state / "ticks"

    def tearDown(self):
        self.root.cleanup()

    def run_brigade(self, *arguments: str):
        return self.machine.run_brigade(CLONE_ENTRY_POINT, *arguments)


class BrigadeTickTrailTest(TrailTestCase):
    def test_should_write_the_trail_of_the_tick(self):
        # Act
        completed = self.run_brigade("tick", "--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        [trail] = self.ticks.iterdir()
        self.assertRegex(trail.name, TICK_TRAIL_PATTERN)


class BrigadeCommandTrailTest(TrailTestCase):
    def setUp(self):
        super().setUp()
        self.environment = {**self.machine.describe_environment(), "PATH": SYSTEMD_USER_MANAGER}

    def run_status(self, *options: str):
        return self.machine.run_brigade(
            CLONE_ENTRY_POINT, "scheduler", "status", *options, environment=self.environment
        )

    def test_should_render_each_record_on_stderr_and_leave_stdout_unchanged_under_verbose(self):
        # Act
        completed = self.run_status("--json", "--verbose")

        # Assert
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(
            completed.stdout,
            '{"schema_version": 1, "scheduler": "none", "unit_files": [], "cron_line": null,'
            ' "next_activation": null, "last_tick": null, "tick_stale_after": 15, "stale": false,'
            ' "paused_waves": [], "parked_tasks": []}\n',
        )
        self.assertEqual(completed.stderr, "brigade scheduler status: ran crontab -l, not on PATH\n")
