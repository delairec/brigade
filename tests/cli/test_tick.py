import fcntl
import json
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine

INSTANT = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
FIRST_TICK_WAIT_S = 10
POLL_INTERVAL_S = 0.05
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
        holder = open(self.lock, "a")
        self.addCleanup(holder.close)
        fcntl.flock(holder, fcntl.LOCK_EX)

    def start_loop(self) -> subprocess.Popen:
        loop = subprocess.Popen(
            [sys.executable, str(CLONE_ENTRY_POINT), "tick", "--loop", "--json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.machine.describe_environment(),
        )
        self.addCleanup(loop.kill)
        return loop

    def wait_for_heartbeat(self) -> None:
        deadline = time.monotonic() + FIRST_TICK_WAIT_S
        while not self.heartbeat.exists() and time.monotonic() < deadline:
            time.sleep(POLL_INTERVAL_S)


class BrigadeTickOnce(TickTestCase):
    def test_should_write_the_heartbeat_of_a_tick_that_applied_no_action(self):
        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        heartbeat = json.loads(self.heartbeat.read_text())
        self.assertRegex(heartbeat["ts"], INSTANT)
        self.assertIsInstance(heartbeat["duration_ms"], int)
        self.assertEqual(
            heartbeat,
            {"schema_version": 1, "ts": heartbeat["ts"], "duration_ms": heartbeat["duration_ms"], "actions_applied": 0},
        )

    def test_should_leave_the_lock_and_the_heartbeat_alone_in_the_state_directory(self):
        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(sorted(path.name for path in self.state.iterdir()), ["locks", "tick.json"])

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
        self.assertRegex(completed.stdout, r"^tick \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z: 0 actions applied in \d+ ms\n$")


class BrigadeTickOnceWhileAnotherTickHoldsTheLock(TickTestCase):
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
        self.assertFalse(self.heartbeat.exists())


class BrigadeTickDryRun(TickTestCase):
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


class BrigadeTickLoop(TickTestCase):
    def test_should_tick_at_once_and_exit_0_on_a_signal(self):
        rows = [("SIGTERM", signal.SIGTERM), ("SIGINT", signal.SIGINT)]
        for name, stop_signal in rows:
            with self.subTest(signal=name):
                # Arrange
                self.heartbeat.unlink(missing_ok=True)
                loop = self.start_loop()
                self.wait_for_heartbeat()

                # Act
                loop.send_signal(stop_signal)

                # Assert
                stdout, stderr = loop.communicate(timeout=STOP_WAIT_S)
                self.assertEqual(loop.returncode, 0, stderr)
                self.assertEqual(json.loads(stdout), {"schema_version": 1, "mode": "loop", "ticks": 1})

    def test_should_report_each_tick_on_stderr(self):
        # Arrange
        loop = self.start_loop()
        self.wait_for_heartbeat()

        # Act
        loop.send_signal(signal.SIGTERM)

        # Assert
        _, stderr = loop.communicate(timeout=STOP_WAIT_S)
        self.assertRegex(stderr, r"^brigade tick: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z: 0 actions applied in \d+ ms\n$")


class BrigadeTickLoopWhileAnotherTickHoldsTheLock(TickTestCase):
    def test_should_stand_down_on_stderr_and_exit_0_on_a_signal(self):
        # Arrange
        self.hold_tick_lock()
        loop = self.start_loop()
        stand_down_line = loop.stderr.readline()

        # Act
        loop.send_signal(signal.SIGTERM)

        # Assert
        stdout, _ = loop.communicate(timeout=STOP_WAIT_S)
        self.assertEqual(
            (stand_down_line, loop.returncode, json.loads(stdout)),
            (f"brigade tick: another tick holds {self.lock}\n", 0, {"schema_version": 1, "mode": "loop", "ticks": 1}),
        )
        self.assertFalse(self.heartbeat.exists())


class BrigadeTickWithoutAMode(TickTestCase):
    def test_should_refuse_with_its_usage(self):
        # Act
        completed = self.run_tick()

        # Assert
        self.assertEqual(completed.returncode, 2)
        self.assertIn("one of the arguments --once --dry-run --loop is required", completed.stderr)
