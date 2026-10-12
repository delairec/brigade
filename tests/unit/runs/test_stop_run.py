import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from brigade.errors import BrigadeError
from brigade.runs.record_run_pid import record_run_pid
from brigade.runs.stop_run import stop_run

RUN_ID = "20261012T090000Z-b136a1"
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


class StopRunOfAProcessReapedBeforeItsSignalTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.state_root = Path(self.root.name) / "brigade"
        run_directory = self.state_root / "runs" / RUN_ID
        run_directory.mkdir(parents=True)
        (run_directory / "run.json").write_text(json.dumps(RUN_RECORD))
        self.living_pid = os.getpid()
        record_run_pid(run_directory, self.living_pid)

    def tearDown(self):
        self.root.cleanup()

    def test_should_refuse_the_run_as_dead_naming_its_pid(self):
        # Arrange
        reaped_before_its_signal = ProcessLookupError(3, "No such process")

        # Act
        with (
            mock.patch.object(os, "kill", side_effect=reaped_before_its_signal),
            self.assertRaises(BrigadeError) as refusal,
        ):
            stop_run(self.state_root, RUN_ID)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            f"run {RUN_ID} is dead: no process of its identity holds its pid {self.living_pid}",
        )
