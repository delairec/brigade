import json
import os
import tempfile
import unittest
from pathlib import Path

from brigade.runs.list_runs import list_runs

RUN_ID = "20261007T090000Z-b70a01"
RUN_RECORD = {"run": RUN_ID, "procedure": "deliver", "slot": "build", "role": "builder", "project": None}
PROCESS_OF_ANOTHER_USER = "1"


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
        self.assertEqual(runs, [{**RUN_RECORD, "state": "dead", "outcome": None}])

    def test_should_list_a_run_whose_pid_is_no_number_as_dead(self):
        # Arrange
        self.start_run()
        (self.run_directory / "pid").write_text("\n")

        # Act
        runs = list_runs(self.state_root)

        # Assert
        self.assertEqual(runs, [{**RUN_RECORD, "state": "dead", "outcome": None}])

    @unittest.skipIf(os.geteuid() == 0, "root may signal every process")
    def test_should_list_a_run_whose_process_belongs_to_another_user_as_running(self):
        # Arrange
        self.start_run()
        (self.run_directory / "pid").write_text(PROCESS_OF_ANOTHER_USER)

        # Act
        runs = list_runs(self.state_root)

        # Assert
        self.assertEqual(runs, [{**RUN_RECORD, "state": "running", "outcome": None}])
