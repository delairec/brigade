import json
import tempfile
import unittest
from pathlib import Path

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine

TRAILS_KEPT_FOR_EVER = "trail_days = 100000\n"
RUN_ID = "20261008T090000Z-a1b2c3"
TICK_ID = "20261009T100000Z"
COMMAND_ID = "20261010T110000Z-scheduler-status"
GIT_STATUS_EXITED_0 = {
    "schema_version": 1,
    "argv": ["git", "status"],
    "cwd": "/work",
    "exit": 0,
    "duration_ms": 12,
    "outcome": "exited",
}
GIT_FETCH_EXITED_128 = {
    "schema_version": 1,
    "argv": ["git", "fetch", "origin"],
    "cwd": "/work",
    "exit": 128,
    "duration_ms": 340,
    "outcome": "exited",
}
CLIENT_CUT = {
    "schema_version": 1,
    "argv": ["claude", "-p", "deliver the task"],
    "cwd": "/work",
    "exit": None,
    "duration_ms": 600000,
    "outcome": "cut",
}
RUN_SPAWNED = {
    "schema_version": 1,
    "argv": ["brigade", "run", "awawa-task", "--detach"],
    "cwd": "/work",
    "exit": None,
    "duration_ms": None,
    "outcome": "spawned",
    "pid": 4242,
}
CRONTAB_NOT_FOUND = {
    "schema_version": 1,
    "argv": ["crontab", "-l"],
    "cwd": "/",
    "exit": None,
    "duration_ms": 3,
    "outcome": "not_found",
}


class ProcessesTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.machine = TemporaryMachine(Path(self.root.name).resolve())
        self.machine.write_configuration(TRAILS_KEPT_FOR_EVER)
        self.state = self.machine.state_home / "brigade"
        self.tick_trail = self.state / "ticks" / f"{TICK_ID}.jsonl"
        self.write_trail(
            self.state / "runs" / RUN_ID / "processes.jsonl", [GIT_STATUS_EXITED_0, GIT_FETCH_EXITED_128, CLIENT_CUT]
        )
        self.write_trail(self.tick_trail, [GIT_STATUS_EXITED_0, RUN_SPAWNED])
        self.write_trail(self.state / "commands" / f"{COMMAND_ID}.jsonl", [CRONTAB_NOT_FOUND])

    def tearDown(self):
        self.root.cleanup()

    def write_trail(self, path: Path, records: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(f"{json.dumps(record)}\n" for record in records))

    def run_brigade(self, *arguments: str):
        return self.machine.run_brigade(CLONE_ENTRY_POINT, "processes", *arguments)


class BrigadeProcessesListTest(ProcessesTestCase):
    def test_should_print_the_invocations_as_a_table_under_its_header(self):
        # Act
        completed = self.run_brigade("list")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout,
            "kind     id                                 instant               processes  failed\n"
            "command  20261010T110000Z-scheduler-status  2026-10-10T11:00:00Z  1          1\n"
            "tick     20261009T100000Z                   2026-10-09T10:00:00Z  2          1\n"
            "run      20261008T090000Z-a1b2c3            2026-10-08T09:00:00Z  3          2\n",
        )
        self.assertEqual(completed.stderr, "")


class BrigadeProcessesShowTest(ProcessesTestCase):
    def test_should_print_the_outcome_the_exit_code_and_the_argv_of_each_record_that_exited(self):
        # Act
        completed = self.run_brigade("show", RUN_ID, "--failed")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout,
            "exited  128  git fetch origin\ncut  600000 ms  claude -p 'deliver the task'\n",
        )
        self.assertEqual(completed.stderr, "")
