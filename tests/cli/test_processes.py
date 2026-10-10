import json
import tempfile
import unittest
from pathlib import Path

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine

TRAILS_KEPT_FOR_EVER = "trail_days = 100000\n"
RUN_ID = "20261008T090000Z-a1b2c3"
TICK_ID = "20261009T100000Z"
COMMAND_ID = "20261010T110000Z-scheduler-status"
UNKNOWN_ID = "20000101T000000Z"
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
RECORD_BEING_WRITTEN = '{"schema_version": 1, "argv": ["claude", "-p", "deliv'
WHOLE_LINE_NOT_A_RECORD = '{"schema_version": 1, "argv": ["claude", "-p", "deliv{"schema_version": 1}\n'


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
    def test_should_list_the_run_the_tick_and_the_command_newest_first_with_their_counts(self):
        # Act
        completed = self.run_brigade("list", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "invocations": [
                    {
                        "kind": "command",
                        "id": COMMAND_ID,
                        "instant": "2026-10-10T11:00:00Z",
                        "processes": 1,
                        "failed": 1,
                    },
                    {"kind": "tick", "id": TICK_ID, "instant": "2026-10-09T10:00:00Z", "processes": 2, "failed": 1},
                    {"kind": "run", "id": RUN_ID, "instant": "2026-10-08T09:00:00Z", "processes": 3, "failed": 2},
                ],
            },
        )

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


class BrigadeProcessesShowTest(ProcessesTestCase):
    def test_should_return_the_records_of_the_run_as_written(self):
        # Act
        completed = self.run_brigade("show", RUN_ID, "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "kind": "run",
                "id": RUN_ID,
                "processes": [GIT_STATUS_EXITED_0, GIT_FETCH_EXITED_128, CLIENT_CUT],
            },
        )

    def test_should_keep_the_records_not_exited_with_code_0_with_failed(self):
        # Act
        completed = self.run_brigade("show", RUN_ID, "--failed", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {"schema_version": 1, "kind": "run", "id": RUN_ID, "processes": [GIT_FETCH_EXITED_128, CLIENT_CUT]},
        )

    def test_should_return_the_records_of_the_tick_by_the_id_list_prints(self):
        # Act
        completed = self.run_brigade("show", TICK_ID, "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {"schema_version": 1, "kind": "tick", "id": TICK_ID, "processes": [GIT_STATUS_EXITED_0, RUN_SPAWNED]},
        )

    def test_should_return_the_records_of_the_command_by_the_id_list_prints(self):
        # Act
        completed = self.run_brigade("show", COMMAND_ID, "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {"schema_version": 1, "kind": "command", "id": COMMAND_ID, "processes": [CRONTAB_NOT_FOUND]},
        )

    def test_should_print_the_outcome_the_exit_code_and_the_argv_of_each_record_that_exited(self):
        # Act
        completed = self.run_brigade("show", RUN_ID, "--failed")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout,
            "exited  128  git fetch origin\ncut  600000 ms  claude -p 'deliver the task'\n",
        )

    def test_should_print_the_duration_of_a_record_with_no_exit_code_and_a_dash_without_either(self):
        rows = [
            ("a command not on PATH", COMMAND_ID, "not_found  3 ms  crontab -l\n"),
            ("a spawned run", TICK_ID, "exited  0  git status\nspawned  -  brigade run awawa-task --detach\n"),
        ]
        for case, invocation_id, expected in rows:
            with self.subTest(case=case):
                # Act
                completed = self.run_brigade("show", invocation_id)

                # Assert
                self.assertEqual((completed.returncode, completed.stdout), (0, expected), completed.stderr)

    def test_should_exit_1_naming_an_id_no_trail_holds(self):
        rows = [("an unknown id", UNKNOWN_ID), ("a path to a trail", f"../runs/{RUN_ID}")]
        for case, invocation_id in rows:
            with self.subTest(case=case):
                # Act
                completed = self.run_brigade("show", invocation_id)

                # Assert
                self.assertEqual(
                    (completed.returncode, completed.stderr),
                    (1, f"brigade processes show: no run, tick or command {invocation_id}\n"),
                )


class BrigadeProcessesUnreadableTrailTest(ProcessesTestCase):
    def test_should_leave_out_of_show_the_record_still_being_written(self):
        # Arrange
        self.tick_trail.write_text(f"{json.dumps(GIT_STATUS_EXITED_0)}\n{RECORD_BEING_WRITTEN}")

        # Act
        completed = self.run_brigade("show", TICK_ID, "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {"schema_version": 1, "kind": "tick", "id": TICK_ID, "processes": [GIT_STATUS_EXITED_0]},
        )

    def test_should_count_in_the_list_only_the_records_written_whole(self):
        # Arrange
        self.tick_trail.write_text(f"{json.dumps(GIT_STATUS_EXITED_0)}\n{RECORD_BEING_WRITTEN}")

        # Act
        completed = self.run_brigade("list", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["invocations"][1],
            {"kind": "tick", "id": TICK_ID, "instant": "2026-10-09T10:00:00Z", "processes": 1, "failed": 0},
        )

    def test_should_exit_1_naming_a_whole_line_that_is_not_a_record(self):
        # Arrange
        self.tick_trail.write_text(f"{json.dumps(GIT_STATUS_EXITED_0)}\n{WHOLE_LINE_NOT_A_RECORD}")
        rows = [("list", ("list",)), ("show", ("show", TICK_ID))]
        for subcommand, arguments in rows:
            with self.subTest(subcommand=subcommand):
                # Act
                completed = self.run_brigade(*arguments)

                # Assert
                self.assertEqual(
                    (completed.returncode, completed.stderr),
                    (
                        1,
                        (
                            f"brigade processes {subcommand}: line 2 of {self.tick_trail} is not a process record:"
                            " not a JSON document\n"
                        ),
                    ),
                )


class BrigadeProcessesStrayFileTest(ProcessesTestCase):
    def test_should_leave_out_of_the_list_a_file_whose_name_is_no_instant(self):
        rows = [
            ("a note among the commands", Path("commands") / "notes.jsonl"),
            ("a note among the ticks", Path("ticks") / "notes.jsonl"),
            ("a directory among the runs", Path("runs") / "notes" / "processes.jsonl"),
        ]
        for case, stray in rows:
            with self.subTest(case=case):
                # Arrange
                self.write_trail(self.state / stray, [GIT_STATUS_EXITED_0])

                # Act
                completed = self.run_brigade("list")

                # Assert
                self.assertEqual(
                    (completed.returncode, completed.stdout),
                    (
                        0,
                        (
                            "kind     id                                 instant               processes  failed\n"
                            "command  20261010T110000Z-scheduler-status  2026-10-10T11:00:00Z  1          1\n"
                            "tick     20261009T100000Z                   2026-10-09T10:00:00Z  2          1\n"
                            "run      20261008T090000Z-a1b2c3            2026-10-08T09:00:00Z  3          2\n"
                        ),
                    ),
                    completed.stderr,
                )

    def test_should_show_a_tick_beside_a_file_whose_name_is_no_instant(self):
        # Arrange
        self.write_trail(self.state / "commands" / "notes.jsonl", [GIT_STATUS_EXITED_0])

        # Act
        completed = self.run_brigade("show", TICK_ID, "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {"schema_version": 1, "kind": "tick", "id": TICK_ID, "processes": [GIT_STATUS_EXITED_0, RUN_SPAWNED]},
        )
