import json
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
    "error_class": "turn_limit",
    "reset": None,
    "message": "Reached the maximum number of turns",
}
COUNTING_CLIENT = 'features = "step_count,tool_grants"\n'
FILE_WAIT_S = 20.0
FILE_POLL_S = 0.05


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
