import fcntl
import json
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine
from tests.process_launcher import ProcessLauncher

INSTANT = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"


def stop_loop(loop: subprocess.Popen) -> tuple[str, str]:
    loop.send_signal(signal.SIGTERM)
    return loop.communicate()


class TickTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.machine = TemporaryMachine(Path(self.root.name).resolve())
        self.state = self.machine.state_home / "brigade"
        self.heartbeat = self.state / "tick.json"
        self.lock = self.state / "locks" / "tick.lock"

    def tearDown(self):
        self.root.cleanup()

    def run_tick(self, *options: str):
        return self.machine.run_brigade(CLONE_ENTRY_POINT, "tick", *options)

    def hold_tick_lock(self) -> None:
        self.lock.parent.mkdir(parents=True)
        holder = self.enterContext(self.lock.open("a"))
        fcntl.flock(holder, fcntl.LOCK_EX)

    def start_loop(self, *options: str) -> subprocess.Popen:
        loop = ProcessLauncher.start(
            [sys.executable, str(CLONE_ENTRY_POINT), "tick", "--loop", *options],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.machine.describe_environment(),
        )
        self.addCleanup(loop.kill)
        return loop

    def wait_for_first_tick(self, loop: subprocess.Popen) -> str:
        return loop.stderr.readline()


class BrigadeTickOnceTest(TickTestCase):
    def test_should_report_the_tick_it_recorded_in_the_versioned_document(self):
        # Act
        completed = self.run_tick("--once", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        heartbeat = json.loads(self.heartbeat.read_text())
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "mode": "once",
                "ts": heartbeat["ts"],
                "duration_ms": heartbeat["duration_ms"],
                "actions_applied": 0,
                "actions_failed": 0,
                "heartbeat": str(self.heartbeat),
            },
        )

    def test_should_print_the_tick_as_text(self):
        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertRegex(
            completed.stdout, r"^tick \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z: 0 actions applied, 0 failed in \d+ ms\n$"
        )


class BrigadeTickOnceWhileAnotherTickHoldsTheLockTest(TickTestCase):
    def test_should_exit_0_with_one_stderr_line_and_write_nothing(self):
        # Arrange
        self.hold_tick_lock()

        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(completed.stderr, f"brigade tick: another tick holds {self.lock}\n")
        self.assertEqual(list(self.state.iterdir()), [self.state / "locks"])


class BrigadeTickDryRunTest(TickTestCase):
    def test_should_print_the_snapshot_and_the_empty_plan_in_the_versioned_document(self):
        # Act
        completed = self.run_tick("--dry-run", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        document = json.loads(completed.stdout)
        self.assertRegex(document["snapshot"]["now"], INSTANT)
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "mode": "dry-run",
                "snapshot": {
                    "schema_version": 1,
                    "now": document["snapshot"]["now"],
                    "waves": [],
                    "projects": [],
                    "studies": [],
                    "live_study_runs": [],
                    "study_runs": 2,
                    "rate_limits": [],
                },
                "plan": [],
            },
        )

    def test_should_print_the_snapshot_and_the_plan_as_text(self):
        # Act
        completed = self.run_tick("--dry-run")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report_lines = completed.stdout.splitlines()
        self.assertRegex(report_lines[1], r"^  now  \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertEqual(
            report_lines,
            [
                "snapshot",
                report_lines[1],
                "  waves  []",
                "  projects  []",
                "  studies  []",
                "  live_study_runs  []",
                "  study_runs  2",
                "  rate_limits  []",
                "plan",
                "  no action",
            ],
        )


class BrigadeTickLoopTest(TickTestCase):
    def test_should_tick_at_once_and_exit_0_on_a_signal(self):
        # Arrange
        loop = self.start_loop("--json")
        self.wait_for_first_tick(loop)

        # Act
        stdout, stderr = stop_loop(loop)

        # Assert
        self.assertEqual(loop.returncode, 0, stderr)
        self.assertEqual(json.loads(stdout), {"schema_version": 1, "mode": "loop", "ticks_attempted": 1})

    def test_should_print_the_ticks_attempted_as_text(self):
        # Arrange
        loop = self.start_loop()
        self.wait_for_first_tick(loop)

        # Act
        stdout, stderr = stop_loop(loop)

        # Assert
        self.assertEqual(loop.returncode, 0, stderr)
        self.assertEqual(stdout, "tick --loop: 1 ticks attempted\n", stderr)


class BrigadeTickWithoutAModeTest(TickTestCase):
    def test_should_refuse_with_its_usage(self):
        # Act
        completed = self.run_tick()

        # Assert
        self.assertEqual(completed.returncode, 2)
        self.assertIn("one of the arguments --once --dry-run --loop is required", completed.stderr)


class BrigadeTickOnceWhereAFileStandsForTheStateDirectoryTest(TickTestCase):
    def test_should_exit_1_naming_the_lock_directory_it_cannot_create(self):
        # Arrange
        self.machine.state_home.write_text("")

        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(completed.stderr, f"brigade tick: cannot write {self.state / 'locks'}: Not a directory\n")
