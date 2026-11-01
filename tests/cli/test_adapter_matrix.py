import json
import tempfile
import unittest
from pathlib import Path

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine

FALLBACKS = {
    "resume": "a fresh launch from the progress file",
    "transcripts": "brigade's journal of the run",
    "actions": "one raw record per line of the client's output",
    "step_count": "steps null and the run held on the clock alone",
    "tool_grants": "the client's unattended mode and a disposable worktree for a reading slot",
    "reset_hour": "now plus thirty minutes",
    "graceful_stop": "the hard cut at the wall-time limit",
}
CLAUDE_CODE_ROW = {
    "name": "claude-code",
    "audience": "supported_client",
    "capabilities": {
        "launch": "full",
        "result": "full",
        "resume": "full",
        "transcripts": "full",
        "actions": "full",
        "step_count": "full",
        "tool_grants": "full",
        "reset_hour": "full",
        "graceful_stop": "full",
    },
    "error": None,
}
VIBE_ROW = {
    "name": "vibe",
    "audience": "supported_client",
    "capabilities": {
        "launch": "full",
        "result": "full",
        "resume": "fallback",
        "transcripts": "full",
        "actions": "fallback",
        "step_count": "full",
        "tool_grants": "full",
        "reset_hour": "fallback",
        "graceful_stop": "fallback",
    },
    "error": None,
}
FAKE_ROW = {
    "name": "fake",
    "audience": "test_suite",
    "capabilities": {
        "launch": "full",
        "result": "full",
        "resume": "fallback",
        "transcripts": "fallback",
        "actions": "fallback",
        "step_count": "fallback",
        "tool_grants": "fallback",
        "reset_hour": "fallback",
        "graceful_stop": "fallback",
    },
    "error": None,
}


class AdapterMatrixTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        root = Path(self.root.name)
        self.machine = TemporaryMachine(root)
        self.directory_without_adapter = root / "bin"
        self.directory_without_adapter.mkdir()

    def tearDown(self):
        self.root.cleanup()

    def run_matrix(self, *arguments: str):
        environment = {**self.machine.describe_environment(), "PATH": str(self.directory_without_adapter)}
        return self.machine.run_brigade(CLONE_ENTRY_POINT, "adapter", "matrix", *arguments, environment=environment)


class BrigadeAdapterMatrixOfTheBuiltInAdaptersTest(AdapterMatrixTestCase):
    def test_should_describe_every_adapter_and_the_fallbacks_in_a_versioned_document(self):
        # Act
        completed = self.run_matrix("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        self.assertEqual(
            json.loads(completed.stdout),
            {"schema_version": 1, "adapters": [CLAUDE_CODE_ROW, VIBE_ROW, FAKE_ROW], "fallbacks": FALLBACKS},
        )
