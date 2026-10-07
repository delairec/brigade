import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from brigade.runs.list_runs import list_runs
from brigade.runs.run_locations import PID_FILE, RESULT_FILE, RUN_RECORD_FILE


def write_run(state_root: Path, run_id: str, record: dict, pid: str | None = None, result: dict | None = None) -> Path:
    run_directory = state_root / "runs" / run_id
    run_directory.mkdir(parents=True)
    (run_directory / RUN_RECORD_FILE).write_text(json.dumps(record))
    if pid is not None:
        (run_directory / PID_FILE).write_text(pid)
    if result is not None:
        (run_directory / RESULT_FILE).write_text(json.dumps(result))
    return run_directory


RECORD = {
    "run": "20261007T120000Z-abcdef",
    "procedure": "review",
    "slot": "bastien",
    "role": "bastien",
    "project": None,
}


class ListRunsTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.state_root = Path(self.root.name)

    def tearDown(self):
        self.root.cleanup()

    def test_should_return_an_empty_list_when_the_runs_directory_does_not_exist(self):
        # Act
        runs = list_runs(self.state_root)

        # Assert
        self.assertEqual(runs, [])

    def test_should_list_a_finished_run(self):
        # Arrange
        write_run(self.state_root, "20261007T120000Z-abcdef", RECORD, result={"outcome": "done"})

        # Act
        runs = list_runs(self.state_root)

        # Assert
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["state"], "finished")
        self.assertEqual(runs[0]["outcome"], "done")

    def test_should_list_a_running_run_whose_pid_is_alive(self):
        # Arrange
        write_run(self.state_root, "20261007T120000Z-abcdef", RECORD, pid=str(os.getpid()))

        # Act
        runs = list_runs(self.state_root)

        # Assert
        self.assertEqual(runs[0]["state"], "running")
        self.assertIsNone(runs[0]["outcome"])

    def test_should_list_a_dead_run_whose_pid_is_gone(self):
        # Arrange
        write_run(self.state_root, "20261007T120000Z-abcdef", RECORD, pid="999999")

        # Act
        runs = list_runs(self.state_root)

        # Assert
        self.assertEqual(runs[0]["state"], "dead")
        self.assertIsNone(runs[0]["outcome"])

    def test_should_list_a_dead_run_whose_pid_file_is_not_a_number(self):
        # Arrange
        write_run(self.state_root, "20261007T120000Z-abcdef", RECORD, pid="not-a-number")

        # Act
        runs = list_runs(self.state_root)

        # Assert
        self.assertEqual(runs[0]["state"], "dead")

    def test_should_list_a_dead_run_whose_pid_file_is_absent(self):
        # Arrange
        write_run(self.state_root, "20261007T120000Z-abcdef", RECORD)

        # Act
        runs = list_runs(self.state_root)

        # Assert
        self.assertEqual(runs[0]["state"], "dead")

    def test_should_list_a_running_run_whose_process_belongs_to_another_user(self):
        # Arrange
        write_run(self.state_root, "20261007T120000Z-abcdef", RECORD, pid="1")

        # Act
        with mock.patch("os.kill", side_effect=PermissionError):
            runs = list_runs(self.state_root)

        # Assert
        self.assertEqual(runs[0]["state"], "running")
