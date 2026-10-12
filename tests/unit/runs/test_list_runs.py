import json
import os
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.runs.list_runs import list_runs
from brigade.runs.record_run_pid import record_run_pid
from brigade.system.read_start_time import read_start_time

RUN_ID = "20261007T090000Z-b70a01"
RUN_RECORD = {
    "schema_version": 1,
    "run": RUN_ID,
    "procedure": "deliver",
    "procedure_path": "built-in",
    "slot": "build",
    "role": "builder",
    "role_source": "built-in",
    "client": "fake",
    "project": None,
    "cwd": "/home/user/tidepool",
    "worktree": "/home/user/tidepool",
    "capabilities": ["read"],
    "budget": 40,
    "wall_limit_s": 1500.0,
    "arguments": {},
}
RUN_RECORD_WITHOUT_CLIENT = {
    "schema_version": 1,
    "run": RUN_ID,
    "procedure": "deliver",
    "procedure_path": "built-in",
    "slot": "build",
    "role": "builder",
    "role_source": "built-in",
    "project": None,
    "cwd": "/home/user/tidepool",
    "worktree": "/home/user/tidepool",
    "capabilities": ["read"],
    "budget": 40,
    "wall_limit_s": 1500.0,
    "arguments": {},
}
ANOTHER_START_TIME = 1
ANOTHER_BOOT_ID = "0f2a4c6e-1b3d-4f5a-8c7e-9d0b2a4c6e8f"
RUN_RESULT = {
    "schema_version": 1,
    "outcome": "done",
    "steps": 12,
    "usage": None,
    "session_id": "session-b74",
    "duration_ms": 4200,
    "error_class": None,
    "reset": None,
    "message": "the client finished the task",
}


class ListRunsTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.state_root = Path(self.root.name) / "brigade"
        self.run_directory = self.state_root / "runs" / RUN_ID

    def tearDown(self):
        self.root.cleanup()

    def start_run(self) -> None:
        self.run_directory.mkdir(parents=True)
        (self.run_directory / "run.json").write_text(json.dumps(RUN_RECORD))


class ListRunsBeforeAnyRunTest(ListRunsTestCase):
    def test_should_list_nothing(self):
        # Act
        runs = list_runs(self.state_root)

        # Assert
        self.assertEqual(runs, [])


class ListRunsOfAnUnfinishedRunTest(ListRunsTestCase):
    def test_should_list_a_run_whose_pid_was_never_written_as_dead(self):
        # Arrange
        self.start_run()

        # Act
        runs = list_runs(self.state_root)

        # Assert
        self.assertEqual(
            runs,
            [
                {
                    "run": "20261007T090000Z-b70a01",
                    "procedure": "deliver",
                    "slot": "build",
                    "role": "builder",
                    "project": None,
                    "state": "dead",
                    "outcome": None,
                }
            ],
        )

    def test_should_list_a_run_whose_process_is_alive_as_running(self):
        # Arrange
        self.start_run()
        record_run_pid(self.run_directory, os.getpid())

        # Act
        [listed] = list_runs(self.state_root)

        # Assert
        self.assertEqual(listed["state"], "running")

    def test_should_list_a_run_whose_pid_holds_a_process_of_another_identity_as_dead(self):
        # Arrange
        living_pid = os.getpid()
        start_time = read_start_time(Path(f"/proc/{living_pid}/stat").read_text())
        boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        rows = [
            ("a living process of another start time", f"{living_pid} {ANOTHER_START_TIME} {boot_id}\n"),
            ("a living process recorded under another boot", f"{living_pid} {start_time} {ANOTHER_BOOT_ID}\n"),
            ("the pid alone, written before the identity", f"{living_pid}\n"),
        ]
        self.start_run()
        for case, written in rows:
            with self.subTest(case=case):
                (self.run_directory / "pid").write_text(written)

                # Act
                [listed] = list_runs(self.state_root)

                # Assert
                self.assertEqual(listed["state"], "dead")


class ListRunsOfAFinishedRunTest(ListRunsTestCase):
    def test_should_list_the_run_finished_with_the_outcome_of_its_result(self):
        # Arrange
        self.start_run()
        (self.run_directory / "result.json").write_text(json.dumps(RUN_RESULT))

        # Act
        [listed] = list_runs(self.state_root)

        # Assert
        self.assertEqual((listed["state"], listed["outcome"]), ("finished", "done"))


class ListRunsOfARefusedDocumentTest(ListRunsTestCase):
    def test_should_refuse_a_run_record_naming_the_file_and_the_problem(self):
        rows = [
            ("a record that is not JSON", "{", "is not a run record: not a JSON document"),
            (
                "a record lacking its client",
                json.dumps(RUN_RECORD_WITHOUT_CLIENT),
                "is not a run record: lacks the key client",
            ),
        ]
        for case, content, expected_problem in rows:
            with self.subTest(case=case):
                # Arrange
                self.run_directory.mkdir(parents=True, exist_ok=True)
                (self.run_directory / "run.json").write_text(content)

                # Act
                with self.assertRaises(BrigadeError) as refusal:
                    list_runs(self.state_root)

                # Assert
                self.assertEqual(str(refusal.exception), f"{self.run_directory / 'run.json'} {expected_problem}")

    def test_should_refuse_a_run_result_naming_the_file_and_the_problem(self):
        # Arrange
        self.start_run()
        (self.run_directory / "result.json").write_text(json.dumps({**RUN_RESULT, "outcome": "lost"}))

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            list_runs(self.state_root)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            f"{self.run_directory / 'result.json'} is not a run result: outcome is 'lost', not one of done, failed,"
            " handed_over, blocked, undeclared, wall_limit, turn_limit, soft_limit, stopped",
        )
