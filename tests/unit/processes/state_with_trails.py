import shutil
import tempfile
import unittest
from pathlib import Path

SUCCEEDED = '{"outcome": "exited", "exit": 0}\n'
EXITED_ONE = '{"outcome": "exited", "exit": 1}\n'
TIMED_OUT = '{"outcome": "timed_out", "exit": null}\n'


class StateWithTrailsTestCase(unittest.TestCase):
    def setUp(self):
        self.state_root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.state_root)
        self.write_trail("runs/20261010T090000Z-b86a01/processes.jsonl", SUCCEEDED + EXITED_ONE)
        self.write_trail("ticks/20261010T100000Z.jsonl", TIMED_OUT)
        self.write_trail("commands/20261010T080000Z-ab12.jsonl", SUCCEEDED)
        self.write_trail("commands/notes.jsonl", SUCCEEDED)

    def write_trail(self, relative: str, text: str) -> Path:
        path = self.state_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path
