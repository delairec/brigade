import fcntl
import json
import os
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import ANY

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine

INSTANT = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
STOP_WAIT_S = 10


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
        holder = self.enterContext(open(self.lock, "a"))
        fcntl.flock(holder, fcntl.LOCK_EX)

    def start_loop(self, *options: str) -> subprocess.Popen:
        loop = subprocess.Popen(  # noqa: S603 - the test's own command line
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
    def test_should_write_the_heartbeat_of_a_tick_that_applied_no_action(self):
        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        heartbeat = json.loads(self.heartbeat.read_text())
        self.assertRegex(heartbeat["ts"], INSTANT)
        self.assertIsInstance(heartbeat["duration_ms"], int)
        self.assertEqual(heartbeat, {"schema_version": 1, "ts": ANY, "duration_ms": ANY, "actions_applied": 0})

    def test_should_leave_the_lock_the_heartbeat_and_the_trails_alone_in_the_state_directory(self):
        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(sorted(path.name for path in self.state.iterdir()), ["locks", "tick.json", "ticks"])

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
                "heartbeat": str(self.heartbeat),
            },
        )

    def test_should_print_the_tick_as_text(self):
        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertRegex(
            completed.stdout, r"^tick \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z: 0 actions applied in \d+ ms\n$"
        )


class BrigadeTickOnceWhileAnotherTickHoldsTheLockTest(TickTestCase):
    def test_should_exit_0_with_one_stderr_line_and_write_nothing(self):
        # Arrange
        self.hold_tick_lock()

        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (0, "", f"brigade tick: another tick holds {self.lock}\n"),
        )
        self.assertEqual(sorted(os.listdir(self.state)), ["locks"])


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
                "snapshot": {"schema_version": 1, "now": document["snapshot"]["now"]},
                "plan": [],
            },
        )

    def test_should_take_no_lock_and_write_no_heartbeat(self):
        # Act
        completed = self.run_tick("--dry-run")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertFalse(self.state.exists())

    def test_should_plan_while_another_tick_holds_the_lock(self):
        # Arrange
        self.hold_tick_lock()

        # Act
        completed = self.run_tick("--dry-run", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["plan"], [])

    def test_should_print_the_snapshot_and_the_plan_as_text(self):
        # Act
        completed = self.run_tick("--dry-run")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report_lines = completed.stdout.splitlines()
        self.assertRegex(report_lines[1], r"^  now  \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertEqual(report_lines, ["snapshot", report_lines[1], "plan", "  no action"])


class BrigadeTickLoopTest(TickTestCase):
    def test_should_tick_at_once_and_exit_0_on_a_signal(self):
        # Arrange
        rows = [("SIGTERM", signal.SIGTERM), ("SIGINT", signal.SIGINT)]
        for name, stop_signal in rows:
            with self.subTest(signal=name):
                # Arrange
                loop = self.start_loop("--json")
                self.wait_for_first_tick(loop)

                # Act
                loop.send_signal(stop_signal)

                # Assert
                stdout, stderr = loop.communicate(timeout=STOP_WAIT_S)
                self.assertEqual(loop.returncode, 0, stderr)
                self.assertEqual(json.loads(stdout), {"schema_version": 1, "mode": "loop", "ticks_attempted": 1})

    def test_should_report_each_tick_on_stderr(self):
        # Arrange
        loop = self.start_loop("--json")
        first_report = self.wait_for_first_tick(loop)

        # Act
        loop.send_signal(signal.SIGTERM)

        # Assert
        _, later_reports = loop.communicate(timeout=STOP_WAIT_S)
        self.assertRegex(
            first_report, r"^brigade tick: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z: 0 actions applied in \d+ ms\n$"
        )
        self.assertEqual(later_reports, "")

    def test_should_print_the_ticks_attempted_as_text(self):
        # Arrange
        loop = self.start_loop()
        self.wait_for_first_tick(loop)

        # Act
        loop.send_signal(signal.SIGTERM)

        # Assert
        stdout, stderr = loop.communicate(timeout=STOP_WAIT_S)
        self.assertEqual((loop.returncode, stdout), (0, "tick --loop: 1 ticks attempted\n"), stderr)

    def test_should_write_the_trail_of_its_first_round(self):
        # Arrange
        loop = self.start_loop()
        self.wait_for_first_tick(loop)

        # Act
        loop.send_signal(signal.SIGTERM)

        # Assert
        loop.communicate(timeout=STOP_WAIT_S)
        [trail] = (self.state / "ticks").iterdir()
        self.assertRegex(trail.name, r"^\d{8}T\d{6}Z\.jsonl$")


class BrigadeTickLoopWhileAnotherTickHoldsTheLockTest(TickTestCase):
    def test_should_stand_down_on_stderr_and_exit_0_on_a_signal(self):
        # Arrange
        self.hold_tick_lock()
        loop = self.start_loop("--json")
        stand_down_line = self.wait_for_first_tick(loop)

        # Act
        loop.send_signal(signal.SIGTERM)

        # Assert
        stdout, _ = loop.communicate(timeout=STOP_WAIT_S)
        self.assertEqual(
            (stand_down_line, loop.returncode, json.loads(stdout)),
            (
                f"brigade tick: another tick holds {self.lock}\n",
                0,
                {"schema_version": 1, "mode": "loop", "ticks_attempted": 1},
            ),
        )
        self.assertFalse(self.heartbeat.exists())


class BrigadeTickWithoutAModeTest(TickTestCase):
    def test_should_refuse_with_its_usage(self):
        # Act
        completed = self.run_tick()

        # Assert
        self.assertEqual(completed.returncode, 2)
        self.assertIn("one of the arguments --once --dry-run --loop is required", completed.stderr)


@unittest.skipIf(os.geteuid() == 0, "root writes where the permissions refuse it")
class BrigadeTickOnceWhereTheMachineRefusesTheStateDirectoryTest(TickTestCase):
    def setUp(self):
        super().setUp()
        self.machine.state_home.mkdir()

    def tearDown(self):
        self.machine.state_home.chmod(0o700)
        super().tearDown()

    def test_should_exit_1_naming_the_state_directory_it_cannot_create(self):
        # Arrange
        self.machine.state_home.chmod(0o500)

        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (1, "", f"brigade tick: cannot write {self.state}: Permission denied\n"),
        )


@unittest.skipIf(os.geteuid() == 0, "root writes where the permissions refuse it")
class BrigadeTickOnceWhereTheMachineRefusesAWriteInTheStateDirectoryTest(TickTestCase):
    def setUp(self):
        super().setUp()
        self.lock.parent.mkdir(parents=True)

    def tearDown(self):
        self.state.chmod(0o700)
        super().tearDown()

    def test_should_exit_1_naming_the_lock_it_cannot_open(self):
        # Arrange
        self.lock.touch(mode=0o400)

        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (1, "", f"brigade tick: cannot write {self.lock}: Permission denied\n"),
        )

    def test_should_exit_1_naming_the_trail_directory_it_cannot_create_and_write_no_heartbeat(self):
        # Arrange
        self.state.chmod(0o500)

        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(
            (
                completed.returncode,
                completed.stdout,
                completed.stderr,
                sorted(path.name for path in self.state.iterdir()),
            ),
            (1, "", f"brigade tick: cannot write {self.state / 'ticks'}: Permission denied\n", ["locks"]),
        )

    def test_should_exit_1_naming_the_heartbeat_it_cannot_write_and_write_none(self):
        # Arrange
        (self.state / "ticks").mkdir()
        self.state.chmod(0o500)

        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr, self.heartbeat.exists()),
            (1, "", f"brigade tick: cannot write {self.heartbeat}: Permission denied\n", False),
        )


@unittest.skipIf(os.geteuid() == 0, "root writes where the permissions refuse it")
class BrigadeTickLoopWhereTheMachineRefusesTheWriteTest(TickTestCase):
    def setUp(self):
        super().setUp()
        self.machine.state_home.mkdir()
        self.machine.state_home.chmod(0o500)

    def tearDown(self):
        self.machine.state_home.chmod(0o700)
        super().tearDown()

    def test_should_report_the_failed_tick_and_keep_ticking_until_a_signal(self):
        # Arrange
        loop = self.start_loop("--json")
        failure_line = self.wait_for_first_tick(loop)

        # Act
        loop.send_signal(signal.SIGTERM)

        # Assert
        stdout, later_reports = loop.communicate(timeout=STOP_WAIT_S)
        self.assertEqual(
            (failure_line, later_reports, loop.returncode, self.state.exists()),
            (f"brigade tick: cannot write {self.state}: Permission denied\n", "", 0, False),
        )
        self.assertEqual(json.loads(stdout), {"schema_version": 1, "mode": "loop", "ticks_attempted": 1})
