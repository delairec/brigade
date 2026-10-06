import json
import os
import tempfile
import unittest
from pathlib import Path

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine

FIXTURES = Path(__file__).resolve().parent / "fixtures"
RECORDINGS = FIXTURES / "recordings"
CLAUDE_CODE_RESULT = FIXTURES / "claude-code" / "result-success.json"
SCRIPTED_CLIENT = str(FIXTURES / "executables" / "client-scripted")
BROKEN_CLIENT = str(FIXTURES / "executables" / "client-broken")

LAUNCH_REQUEST = (
    '{"schema_version": 1, "worktree": "/srv/b42", "brief": "Deliver the task B42.", "role": {"name": "bastien",'
    ' "package": "AGENT bastien", "capabilities": ["read"], "reasoning": "standard", "budget": 75}}'
)
RESUME_REQUEST = (
    '{"schema_version": 1, "worktree": "/srv/b42", "brief": "Carry on.", "session_id": "s1", "role": {"name": "bastien",'
    ' "package": "AGENT bastien", "capabilities": ["read"], "reasoning": "standard", "budget": 75}}'
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

    def run_adapter(self, *arguments: str, request: str | None = None, path_directories: tuple = ()):
        environment = {**self.machine.describe_environment(), "PATH": os.pathsep.join([*path_directories, os.environ["PATH"]])}
        return self.machine.run_brigade(CLONE_ENTRY_POINT, "adapter", *arguments, environment=environment, request=request)


class BrigadeAdapterProbe(AdapterTestCase):
    def test_should_print_the_probe_of_the_configured_client_as_a_document(self):
        # Arrange
        self.machine.write_configuration('client = "fake"\n')

        # Act
        completed = self.run_adapter("probe", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout), FAKE_PROBE)

    def test_should_print_the_probe_as_indented_text(self):
        # Arrange
        self.machine.write_configuration('client = "fake"\n')

        # Act
        completed = self.run_adapter("probe")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout,
            '{\n  "schema_version": 1,\n  "client": "fake",\n  "version_argv": null,\n  "operations": [\n'
            '    "probe",\n    "launch",\n    "result"\n  ],\n  "features": [],\n  "models": {}\n}\n',
        )

    def test_should_answer_through_an_executable_adapter_on_path(self):
        # Arrange
        self.machine.write_configuration('client = "scripted"\n')

        # Act
        completed = self.run_adapter("probe", "--json", path_directories=(SCRIPTED_CLIENT,))

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "client": "scripted",
                "version_argv": None,
                "operations": ["probe", "launch", "result"],
                "features": [],
                "models": {},
            },
        )


class BrigadeAdapterLaunchArgv(AdapterTestCase):
    def test_should_take_the_reasoning_row_config_toml_sets(self):
        # Arrange
        self.machine.write_configuration('client = "claude-code"\n[reasoning.standard]\nmodel = "sonnet"\neffort = "low"\n')

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
                    "json",
                    "--model",
                    "sonnet",
                    "--effort",
                    "low",
                    "--max-turns",
                    "94",
                    "--append-system-prompt",
                    "AGENT bastien",
                    "--allowedTools",
                    "Read,Glob,Grep",
                ],
                "environment": {},
                "stdin": "Deliver the task B42.",
            },
        )

    def test_should_point_the_fake_at_the_recording_of_the_role_in_the_configured_directory(self):
        # Arrange
        self.machine.write_configuration(f'client = "fake"\n[clients.fake]\nrecordings = "{RECORDINGS}"\n')

        # Act
        completed = self.run_adapter("launch-argv", "--json", request=LAUNCH_REQUEST)

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {"schema_version": 1, "argv": ["cat", "--", f"{RECORDINGS}/bastien.json"], "environment": {}, "stdin": None},
        )


class BrigadeAdapterParseResult(AdapterTestCase):
    def test_should_normalise_a_recorded_claude_code_result(self):
        # Arrange
        self.machine.write_configuration('client = "claude-code"\n')
        request = json.dumps({"schema_version": 1, "exit_code": 0, "stdout": CLAUDE_CODE_RESULT.read_text(), "stderr": ""})

        # Act
        completed = self.run_adapter("parse-result", "--json", request=request)

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "outcome": "done",
                "steps": 1,
                "usage": {
                    "input_tokens": 9,
                    "output_tokens": 55,
                    "cache_creation_input_tokens": 16778,
                    "cache_read_input_tokens": 13803,
                },
                "session_id": "ada28962-e848-49c0-8c36-97c10781d78f",
                "duration_ms": 1369,
                "error_class": None,
                "reset": None,
                "message": None,
            },
        )

    def test_should_replay_the_recorded_result_document_through_the_fake(self):
        # Arrange
        self.machine.write_configuration('client = "fake"\n')
        request = json.dumps({"schema_version": 1, "exit_code": 0, "stdout": (RECORDINGS / "bastien.json").read_text(), "stderr": ""})

        # Act
        completed = self.run_adapter("parse-result", "--json", request=request)

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "outcome": "done",
                "steps": 12,
                "usage": {
                    "input_tokens": 120,
                    "output_tokens": 3400,
                    "cache_creation_input_tokens": 16778,
                    "cache_read_input_tokens": 98000,
                },
                "session_id": "fake-session-bastien",
                "duration_ms": 61000,
                "error_class": None,
                "reset": None,
                "message": None,
            },
        )


class BrigadeAdapterResumeArgv(AdapterTestCase):
    def test_should_resume_the_session_the_request_names(self):
        # Arrange
        self.machine.write_configuration('client = "claude-code"\n')

        # Act
        completed = self.run_adapter("resume-argv", "--json", request=RESUME_REQUEST)

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["argv"][4:6], ["--resume", "s1"])


class BrigadeAdapterTranscripts(AdapterTestCase):
    def test_should_read_the_session_under_the_home_directory_of_the_machine(self):
        # Arrange
        self.machine.write_configuration('client = "claude-code"\n')
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
                "messages": [{"role": "user", "timestamp": "2026-10-06T10:00:00.000Z", "content": "Deliver the task B42."}],
            },
        )


class BrigadeAdapterWhenItCannotAnswer(AdapterTestCase):
    def test_should_name_brigade_init_when_no_configuration_exists(self):
        # Act
        completed = self.run_adapter("probe", "--json")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(
            completed.stderr, f"brigade adapter: no configuration at {self.machine.corpus / 'config.toml'}; run brigade init\n"
        )

    def test_should_name_the_client_key_and_the_file_when_no_client_is_configured(self):
        # Arrange
        configuration = self.machine.write_configuration('# client = "claude-code"\n')

        # Act
        completed = self.run_adapter("probe", "--json")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(completed.stderr, f"brigade adapter: config.toml names no client: set the client key in {configuration}\n")

    def test_should_name_an_adapter_found_nowhere(self):
        # Arrange
        self.machine.write_configuration('client = "frobnicate"\n')

        # Act
        completed = self.run_adapter("probe", "--json")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr,
            "brigade adapter: no client adapter frobnicate: no built-in module and no brigade-client-frobnicate on PATH\n",
        )

    def test_should_not_take_a_helper_module_of_the_adapters_for_an_adapter(self):
        # Arrange
        self.machine.write_configuration('client = "describe-unreadable-output"\n')

        # Act
        completed = self.run_adapter("probe", "--json")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr,
            "brigade adapter: no client adapter describe-unreadable-output: no built-in module and no"
            " brigade-client-describe-unreadable-output on PATH\n",
        )

    def test_should_name_the_adapter_the_operation_and_the_key_of_an_answer_off_its_shape(self):
        # Arrange
        self.machine.write_configuration('client = "broken"\n')

        # Act
        completed = self.run_adapter("probe", "--json", path_directories=(BROKEN_CLIENT,))

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(completed.stderr, "brigade adapter: client adapter broken answered probe: lacks the key version_argv\n")

    def test_should_name_the_failed_command_of_an_executable_adapter(self):
        # Arrange
        self.machine.write_configuration('client = "scripted"\n')

        # Act
        completed = self.run_adapter("launch-argv", "--json", request=LAUNCH_REQUEST, path_directories=(SCRIPTED_CLIENT,))

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr,
            f"brigade adapter: {SCRIPTED_CLIENT}/brigade-client-scripted launch-argv exited 3:"
            " brigade-client-scripted answers probe only\n",
        )

    def test_should_name_an_operation_the_adapter_does_not_answer(self):
        # Arrange
        self.machine.write_configuration('client = "fake"\n')

        # Act
        completed = self.run_adapter("resume-argv", "--json", request=RESUME_REQUEST)

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, "brigade adapter: the fake client adapter does not answer resume-argv\n")

    def test_should_name_the_key_a_request_lacks(self):
        # Arrange
        self.machine.write_configuration('client = "claude-code"\n')

        # Act
        completed = self.run_adapter(
            "launch-argv", "--json", request='{"schema_version": 1, "worktree": "/srv/b42", "brief": "Deliver the task B42."}'
        )

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, "brigade adapter: the request on stdin: lacks the key role\n")

    def test_should_refuse_an_invalid_request_before_reading_the_configuration(self):
        # Arrange
        request_lacking_its_role = '{"schema_version": 1, "worktree": "/srv/b42", "brief": "Deliver the task B42."}'

        # Act
        completed = self.run_adapter("launch-argv", "--json", request=request_lacking_its_role)

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(completed.stderr, "brigade adapter: the request on stdin: lacks the key role\n")

    def test_should_refuse_a_request_that_is_not_json(self):
        # Arrange
        self.machine.write_configuration('client = "claude-code"\n')

        # Act
        completed = self.run_adapter("launch-argv", "--json", request="role: bastien")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertIn("brigade adapter: the request on stdin is not JSON: ", completed.stderr)


class BrigadeAdapterOnAnUnexpectedError(AdapterTestCase):
    def test_should_exit_70_with_the_traceback(self):
        # Arrange
        (self.machine.corpus / "config.toml").mkdir(parents=True)

        # Act
        completed = self.run_adapter("probe", "--json")

        # Assert
        self.assertEqual(completed.returncode, 70)
        self.assertEqual(completed.stdout, "")
        self.assertIn("IsADirectoryError", completed.stderr)
