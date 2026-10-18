import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.runs.list_runs import list_runs
from brigade.runs.record_run_pid import record_run_pid

RUN_ID = "20261006T120000Z-abcdef"
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
    "wave": None,
    "task": None,
    "brief": None,
}
WRITE_CALL = "write"
PID_HELD_BY_NO_PROCESS = 2**31 - 1


def list_state_at_the_first_write(state_root: Path, run_directory: Path, pid: int) -> list[str]:
    states = []

    def list_runs_on_the_first_write(_frame, event, called) -> None:
        if event == "c_call" and called.__name__ == WRITE_CALL and not states:
            states.extend(run["state"] for run in list_runs(state_root)["runs"])

    sys.setprofile(list_runs_on_the_first_write)
    try:
        record_run_pid(run_directory, pid)
    finally:
        sys.setprofile(None)
    return states


class RecordRunPidTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.state_root = Path(self.root.name) / "state"
        self.run_directory = self.state_root / "runs" / RUN_ID
        self.run_directory.mkdir(parents=True)
        (self.run_directory / "run.json").write_text(json.dumps(RUN_RECORD))

    def test_should_write_the_pid_its_start_time_and_the_boot_id_on_one_line(self):
        # Arrange
        living_pid = os.getpid()
        boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip()

        # Act
        record_run_pid(self.run_directory, living_pid)

        # Assert
        self.assertRegex((self.run_directory / "pid").read_text(encoding="utf-8"), rf"^{living_pid} \d+ {boot_id}\n$")

    def test_should_refuse_a_pid_no_process_holds_and_write_no_pid_file(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            record_run_pid(self.run_directory, PID_HELD_BY_NO_PROCESS)

        # Assert
        self.assertEqual(str(refusal.exception), "no process holds pid 2147483647")
        self.assertFalse((self.run_directory / "pid").exists())

    def test_should_keep_a_living_run_listed_as_running_while_its_pid_is_written_again(self):
        # Arrange
        living_pid = os.getpid()
        record_run_pid(self.run_directory, living_pid)

        # Act
        states = list_state_at_the_first_write(self.state_root, self.run_directory, living_pid)

        # Assert
        self.assertEqual(states, ["running"])
