import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine

PROCEDURE = "---\ncapabilities: read, write, shell\nbudget: 75\n---\nDeliver the task the brief names.\n"
DONE_RESULT = {
    "schema_version": 1,
    "outcome": "done",
    "steps": 12,
    "usage": {
        "input_tokens": 120,
        "output_tokens": 3400,
        "cache_creation_input_tokens": 16778,
        "cache_read_input_tokens": 98000,
    },
    "session_id": "fake-session",
    "duration_ms": 61000,
    "cost_usd": 0.42,
    "error_class": None,
    "reset": None,
    "message": None,
}
TURN_LIMIT_RESULT = {
    "schema_version": 1,
    "outcome": "failed",
    "steps": 94,
    "usage": None,
    "session_id": "fake-session",
    "duration_ms": 900000,
    "cost_usd": None,
    "error_class": "turn_limit",
    "reset": None,
    "message": "Reached the maximum number of turns",
}
COUNTING_CLIENT = 'features = "step_count,tool_grants"\n'
FILE_WAIT_S = 20.0
FILE_POLL_S = 0.05
NO_SIGNAL = 0


class RunTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        root = Path(self.root.name)
        self.machine = TemporaryMachine(root)
        self.recordings = root / "recordings"
        self.recordings.mkdir()
        self.workspace = root / "workspace"
        self.workspace.mkdir()
        self.procedure = root / "procedures" / "deliver.md"
        self.procedure.parent.mkdir()
        self.procedure.write_text(PROCEDURE)
        self.runs = self.machine.state_home / "brigade" / "runs"
        self.ledger = self.machine.state_home / "brigade" / "ledger"

    def tearDown(self):
        self.root.cleanup()

    def configure_fake(self, settings: str = "", keys: str = "") -> None:
        self.machine.write_configuration(
            f'client = "fake"\n{keys}[clients.fake]\nrecordings = "{self.recordings}"\n{settings}'
        )

    def record(self, role: str, result: dict) -> None:
        (self.recordings / f"{role}.json").write_text(json.dumps(result))

    def run_brigade(self, *arguments: str):
        return self.machine.run_brigade(CLONE_ENTRY_POINT, *arguments)

    def record_lines(self, role: str, recording: str) -> None:
        (self.recordings / f"{role}.json").write_text(recording)

    def read_events(self, name: str) -> list:
        lines = "".join(path.read_text() for path in sorted(self.ledger.glob("*.jsonl"))).splitlines()
        return [event for event in map(json.loads, lines) if event["event"] == name]

    def read_run_record(self, run_id: str) -> dict:
        return json.loads((self.runs / run_id / "run.json").read_text())

    def wait_for_file(self, path: Path) -> None:
        deadline = time.monotonic() + FILE_WAIT_S
        while not path.exists():
            if time.monotonic() > deadline:
                self.fail(f"{path} never appeared")
            time.sleep(FILE_POLL_S)

    def wait_for_line(self, path: Path) -> None:
        deadline = time.monotonic() + FILE_WAIT_S
        while not path.exists() or not path.read_text().strip():
            if time.monotonic() > deadline:
                self.fail(f"{path} never held a line")
            time.sleep(FILE_POLL_S)

    def wait_for_exit(self, pid: int) -> None:
        deadline = time.monotonic() + FILE_WAIT_S
        while True:
            try:
                os.kill(pid, NO_SIGNAL)
            except ProcessLookupError:
                return
            if time.monotonic() > deadline:
                self.fail(f"the process {pid} never exited")
            time.sleep(FILE_POLL_S)

    def read_run_pid(self, run_id: str) -> int:
        pid, _start_time, _boot_id = (self.runs / run_id / "pid").read_text().split()
        return int(pid)

    def wait_for_client(self, brigade_pid: int) -> int:
        children = Path(f"/proc/{brigade_pid}/task/{brigade_pid}/children")
        deadline = time.monotonic() + FILE_WAIT_S
        while not children.read_text().strip():
            if time.monotonic() > deadline:
                self.fail(f"brigade {brigade_pid} never spawned its client")
            time.sleep(FILE_POLL_S)
        return int(children.read_text().split()[0])

    def assert_process_gone(self, pid: int) -> None:
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, NO_SIGNAL)

    def read_every_state_file(self) -> str:
        files = sorted(path for path in self.machine.state_home.rglob("*") if path.is_file())
        return "".join(path.read_text(encoding="utf-8", errors="replace") for path in files)
