import json
import tempfile
import unittest
from pathlib import Path

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine

FIXTURES = Path(__file__).resolve().parent / "fixtures"
REVIEW_ON_ANOTHER_CLIENT = '[slot_clients]\nreview = "finishing"\n'
CLAUDE_CODE_RESULT = FIXTURES / "claude-code" / "result-success.json"

LAUNCH_REQUEST = (
    '{"schema_version": 1, "worktree": "/srv/b42", "brief": "Deliver the task B42.", "session_id": "s1", "stop_at": null,'
    ' "progress_file": "/state/brigade/runs/r1/progress.md", "role": {"name": "builder", "package": "AGENT builder",'
    ' "package_file": "/state/brigade/runs/r1/role.md", "capabilities": ["read"], "reasoning": "standard",'
    ' "budget": 75}}'
)
RESUME_REQUEST = (
    '{"schema_version": 1, "worktree": "/srv/b42", "brief": "Carry on.", "session_id": "s1", "stop_at": null,'
    ' "progress_file": "/state/brigade/runs/r1/progress.md", "role": {"name": "builder", "package": "AGENT builder",'
    ' "package_file": "/state/brigade/runs/r1/role.md", "capabilities": ["read"], "reasoning": "standard",'
    ' "budget": 75}}'
)
FAKE_PROBE = {
    "schema_version": 1,
    "client": "fake",
    "version_argv": None,
    "operations": ["probe", "launch", "result"],
    "features": [],
    "models": {},
}


class AdapterTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.machine = TemporaryMachine(Path(self.root.name))

    def tearDown(self):
        self.root.cleanup()

    def run_adapter(self, *arguments: str, request: str | None = None):
        return self.machine.run_brigade(
            CLONE_ENTRY_POINT, "adapter", *arguments, environment=self.machine.describe_environment(), request=request
        )


class BrigadeAdapterProbeTest(AdapterTestCase):
    def test_should_print_the_probe_of_the_configured_client_and_name_the_slot_bound_to_another_client(self):
        # Arrange
        self.machine.write_configuration('client = "fake"\n' + REVIEW_ON_ANOTHER_CLIENT)

        # Act
        completed = self.run_adapter("probe", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout), FAKE_PROBE)
        self.assertEqual(
            completed.stderr,
            "brigade adapter probe: answers for fake\nbrigade adapter probe: slot review runs on finishing\n",
        )


class BrigadeAdapterLaunchArgvTest(AdapterTestCase):
    def test_should_take_the_reasoning_row_config_toml_sets(self):
        # Arrange
        self.machine.write_configuration(
            'client = "claude-code"\n[reasoning.standard]\nmodel = "sonnet"\neffort = "low"\n'
            + REVIEW_ON_ANOTHER_CLIENT
        )

        # Act
        completed = self.run_adapter("launch-argv", "--json", request=LAUNCH_REQUEST)

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "argv": [
                    "claude",
                    "--print",
                    "--output-format",
                    "stream-json",
                    "--verbose",
                    "--permission-mode",
                    "dontAsk",
                    "--session-id",
                    "s1",
                    "--model",
                    "sonnet",
                    "--effort",
                    "low",
                    "--max-turns",
                    "94",
                    "--append-system-prompt-file",
                    "/state/brigade/runs/r1/role.md",
                    "--allowedTools",
                    "Read,Glob,Grep,Write(//state/brigade/runs/r1/progress.md),Edit(//state/brigade/runs/r1/progress.md)",
                ],
                "environment": {},
                "stdin": "Deliver the task B42.",
                "session_id": "s1",
            },
        )
        self.assertEqual(
            completed.stderr,
            "brigade adapter launch-argv: answers for claude-code\n"
            "brigade adapter launch-argv: slot review runs on finishing\n",
        )


class BrigadeAdapterParseResultTest(AdapterTestCase):
    def test_should_normalise_a_recorded_claude_code_result(self):
        # Arrange
        self.machine.write_configuration('client = "claude-code"\n' + REVIEW_ON_ANOTHER_CLIENT)
        request = json.dumps(
            {"schema_version": 1, "exit_code": 0, "stdout": CLAUDE_CODE_RESULT.read_text(), "stderr": ""}
        )

        # Act
        completed = self.run_adapter("parse-result", "--json", request=request)

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "outcome": "undeclared",
                "steps": 1,
                "usage": {
                    "input_tokens": 9,
                    "output_tokens": 55,
                    "cache_creation_input_tokens": 16778,
                    "cache_read_input_tokens": 13803,
                },
                "session_id": "ada28962-e848-49c0-8c36-97c10781d78f",
                "duration_ms": 1369,
                "cost_usd": 0.0352203,
                "error_class": None,
                "reset": None,
                "message": None,
            },
        )
        self.assertEqual(
            completed.stderr,
            "brigade adapter parse-result: answers for claude-code\n"
            "brigade adapter parse-result: slot review runs on finishing\n",
        )


class BrigadeAdapterResumeArgvTest(AdapterTestCase):
    def test_should_resume_the_session_the_request_names(self):
        # Arrange
        self.machine.write_configuration('client = "claude-code"\n' + REVIEW_ON_ANOTHER_CLIENT)

        # Act
        completed = self.run_adapter("resume-argv", "--json", request=RESUME_REQUEST)

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["argv"],
            [
                "claude",
                "--print",
                "--output-format",
                "stream-json",
                "--verbose",
                "--permission-mode",
                "dontAsk",
                "--resume",
                "s1",
                "--model",
                "opus",
                "--effort",
                "high",
                "--max-turns",
                "94",
                "--append-system-prompt-file",
                "/state/brigade/runs/r1/role.md",
                "--allowedTools",
                "Read,Glob,Grep,Write(//state/brigade/runs/r1/progress.md),Edit(//state/brigade/runs/r1/progress.md)",
            ],
        )
        self.assertEqual(
            completed.stderr,
            "brigade adapter resume-argv: answers for claude-code\n"
            "brigade adapter resume-argv: slot review runs on finishing\n",
        )


class BrigadeAdapterTranscriptsTest(AdapterTestCase):
    def test_should_read_the_session_under_the_home_directory_of_the_machine(self):
        # Arrange
        self.machine.write_configuration('client = "claude-code"\n' + REVIEW_ON_ANOTHER_CLIENT)
        session_directory = self.machine.home / ".claude" / "projects" / "-srv-b42"
        session_directory.mkdir(parents=True)
        (session_directory / "s1.jsonl").write_text(
            '{"type":"user","timestamp":"2026-10-06T10:00:00.000Z","message":{"role":"user","content":"Deliver the task B42."}}\n'
        )

        # Act
        completed = self.run_adapter(
            "transcripts", "--json", request='{"schema_version": 1, "session_id": "s1", "worktree": "/srv/b42"}'
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "messages": [
                    {
                        "role": "user",
                        "timestamp": "2026-10-06T10:00:00.000Z",
                        "content": "Deliver the task B42.",
                        "tool_calls": 0,
                        "tools": [],
                        "id": None,
                        "usage": None,
                    }
                ],
                "subagents": [],
            },
        )
        self.assertEqual(
            completed.stderr,
            "brigade adapter transcripts: answers for claude-code\n"
            "brigade adapter transcripts: slot review runs on finishing\n",
        )


class BrigadeAdapterActionsTest(AdapterTestCase):
    def test_should_read_the_actions_of_the_output_the_request_carries(self):
        # Arrange
        self.machine.write_configuration('client = "claude-code"\n' + REVIEW_ON_ANOTHER_CLIENT)
        request = json.dumps(
            {
                "schema_version": 1,
                "output": '{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"Reading."}]}}\n',
            }
        )

        # Act
        completed = self.run_adapter("actions", "--json", request=request)

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout), {"schema_version": 1, "actions": [{"kind": "text", "summary": "Reading."}]}
        )
        self.assertEqual(
            completed.stderr,
            "brigade adapter actions: answers for claude-code\nbrigade adapter actions: slot review runs on finishing\n",
        )
