import json
import os
import tempfile
import unittest
from pathlib import Path

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine

FIXTURES = Path(__file__).resolve().parent / "fixtures"
RECORDINGS = FIXTURES / "recordings"
CLAUDE_CODE_RESULT = FIXTURES / "claude-code" / "result-success.json"
CLAUDE_CODE_RESULT_AFTER_NOTIFICATION = FIXTURES / "claude-code" / "result-after-task-notification.json"
SCRIPTED_CLIENT = str(FIXTURES / "executables" / "client-scripted")
BROKEN_CLIENT = str(FIXTURES / "executables" / "client-broken")
TRANSCRIPTS_REQUEST = '{"schema_version": 1, "session_id": "s1", "worktree": "/srv/b42"}'
ACTIONS_REQUEST = '{"schema_version": 1, "output": ""}'

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

    def run_adapter(self, *arguments: str, request: str | None = None, path_directories: tuple = ()):
        environment = {
            **self.machine.describe_environment(),
            "PATH": os.pathsep.join([*path_directories, self.machine.search_path]),
        }
        return self.machine.run_brigade(
            CLONE_ENTRY_POINT, "adapter", *arguments, environment=environment, request=request
        )


class BrigadeAdapterProbeTest(AdapterTestCase):
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


class BrigadeAdapterLaunchArgvTest(AdapterTestCase):
    def test_should_take_the_reasoning_row_config_toml_sets(self):
        # Arrange
        self.machine.write_configuration(
            'client = "claude-code"\n[reasoning.standard]\nmodel = "sonnet"\neffort = "low"\n'
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

    def test_should_point_the_fake_at_the_recording_of_the_role_in_the_configured_directory(self):
        # Arrange
        self.machine.write_configuration(f'client = "fake"\n[clients.fake]\nrecordings = "{RECORDINGS}"\n')

        # Act
        completed = self.run_adapter("launch-argv", "--json", request=LAUNCH_REQUEST)

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "argv": ["cat", "--", f"{RECORDINGS}/builder.json"],
                "environment": {},
                "stdin": None,
                "session_id": "s1",
            },
        )


class BrigadeAdapterParseResultTest(AdapterTestCase):
    def test_should_normalise_a_recorded_claude_code_result(self):
        # Arrange
        self.machine.write_configuration('client = "claude-code"\n')
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

    def test_should_report_the_whole_session_of_a_result_that_follows_a_task_notification(self):
        # Arrange
        self.machine.write_configuration('client = "claude-code"\n')
        request = json.dumps(
            {
                "schema_version": 1,
                "exit_code": 0,
                "stdout": CLAUDE_CODE_RESULT_AFTER_NOTIFICATION.read_text(),
                "stderr": "",
            }
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
                "steps": None,
                "usage": {
                    "input_tokens": 108,
                    "output_tokens": 42255,
                    "cache_creation_input_tokens": 230745,
                    "cache_read_input_tokens": 5861342,
                },
                "session_id": "857d4221-e962-4128-8096-759d8feb0ced",
                "duration_ms": 19091,
                "cost_usd": 3.6302823999999987,
                "error_class": None,
                "reset": None,
                "message": None,
            },
        )

    def test_should_replay_the_recorded_result_document_through_the_fake(self):
        # Arrange
        self.machine.write_configuration('client = "fake"\n')
        request = json.dumps(
            {"schema_version": 1, "exit_code": 0, "stdout": (RECORDINGS / "builder.json").read_text(), "stderr": ""}
        )

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
                "session_id": "fake-session-builder",
                "duration_ms": 61000,
                "cost_usd": 0.42,
                "error_class": None,
                "reset": None,
                "message": None,
            },
        )


class BrigadeAdapterResumeArgvTest(AdapterTestCase):
    def test_should_resume_the_session_the_request_names(self):
        # Arrange
        self.machine.write_configuration('client = "claude-code"\n')

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


class BrigadeAdapterTranscriptsTest(AdapterTestCase):
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
                "messages": [
                    {
                        "role": "user",
                        "timestamp": "2026-10-06T10:00:00.000Z",
                        "content": "Deliver the task B42.",
                        "tool_calls": 0,
                        "id": None,
                        "usage": None,
                    }
                ],
                "subagents": [],
            },
        )


class BrigadeAdapterActionsTest(AdapterTestCase):
    def test_should_read_the_actions_of_the_output_the_request_carries(self):
        # Arrange
        self.machine.write_configuration('client = "claude-code"\n')
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

    def test_should_print_the_actions_as_indented_text(self):
        # Arrange
        self.machine.write_configuration('client = "claude-code"\n')
        request = json.dumps(
            {
                "schema_version": 1,
                "output": '{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"Reading."}]}}\n',
            }
        )

        # Act
        completed = self.run_adapter("actions", request=request)

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout,
            '{\n  "schema_version": 1,\n  "actions": [\n    {\n      "kind": "text",\n      "summary": "Reading."\n    }\n  ]\n}\n',
        )

    def test_should_name_the_key_a_request_lacks(self):
        # Arrange
        self.machine.write_configuration('client = "claude-code"\n')

        # Act
        completed = self.run_adapter("actions", request='{"schema_version": 1}')

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, "brigade adapter actions: the request on stdin: lacks the key output\n")


class BrigadeAdapterOnAMachineBindingASlotToAnotherClientTest(AdapterTestCase):
    def test_should_state_the_client_it_answers_for_and_the_slot_bound_to_another_client(self):
        # Arrange
        self.machine.write_configuration(
            'client = "claude-code"\n[slot_clients]\nbuild = "claude-code"\nreview = "finishing"\n'
        )
        parse_result_request = json.dumps(
            {"schema_version": 1, "exit_code": 0, "stdout": CLAUDE_CODE_RESULT.read_text(), "stderr": ""}
        )
        session_directory = self.machine.home / ".claude" / "projects" / "-srv-b42"
        session_directory.mkdir(parents=True)
        (session_directory / "s1.jsonl").write_text(
            '{"type":"user","timestamp":"2026-10-06T10:00:00.000Z","message":{"role":"user","content":"Deliver the task B42."}}\n'
        )
        rows = [
            ("probe", None),
            ("launch-argv", LAUNCH_REQUEST),
            ("resume-argv", RESUME_REQUEST),
            ("parse-result", parse_result_request),
            ("transcripts", TRANSCRIPTS_REQUEST),
            ("actions", ACTIONS_REQUEST),
        ]
        for operation, request in rows:
            with self.subTest(operation=operation):
                # Act
                completed = self.run_adapter(operation, "--json", request=request)

                # Assert
                self.assertEqual(
                    (completed.returncode, completed.stderr),
                    (
                        0,
                        (
                            f"brigade adapter {operation}: answers for claude-code\n"
                            f"brigade adapter {operation}: slot review runs on finishing\n"
                        ),
                    ),
                )


class BrigadeAdapterWhenItCannotAnswerTest(AdapterTestCase):
    def test_should_name_brigade_init_when_no_configuration_exists(self):
        # Act
        completed = self.run_adapter("probe", "--json")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(
            completed.stderr,
            f"brigade adapter probe: no configuration at {self.machine.corpus / 'config.toml'}; run brigade init\n",
        )

    def test_should_name_the_client_key_and_the_file_when_no_client_is_configured(self):
        # Arrange
        configuration = self.machine.write_configuration('# client = "claude-code"\n')

        # Act
        completed = self.run_adapter("probe", "--json")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(
            completed.stderr,
            f"brigade adapter probe: config.toml names no client: set the client key in {configuration}\n",
        )

    def test_should_name_an_adapter_found_nowhere(self):
        # Arrange
        self.machine.write_configuration('client = "frobnicate"\n')

        # Act
        completed = self.run_adapter("probe", "--json")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr,
            "brigade adapter probe: no client adapter frobnicate: no built-in module and no brigade-client-frobnicate on PATH\n",
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
            "brigade adapter probe: no client adapter describe-unreadable-output: no built-in module and no"
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
        self.assertEqual(
            completed.stderr,
            "brigade adapter probe: client adapter broken answered probe: lacks the key version_argv\n",
        )

    def test_should_name_the_failed_command_of_an_executable_adapter(self):
        # Arrange
        self.machine.write_configuration('client = "scripted"\n')

        # Act
        completed = self.run_adapter(
            "launch-argv", "--json", request=LAUNCH_REQUEST, path_directories=(SCRIPTED_CLIENT,)
        )

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr,
            f"brigade adapter launch-argv: {SCRIPTED_CLIENT}/brigade-client-scripted launch-argv exited 3:"
            " brigade-client-scripted answers probe only\n",
        )

    def test_should_name_an_operation_the_adapter_does_not_answer(self):
        # Arrange
        self.machine.write_configuration('client = "fake"\n')

        # Act
        completed = self.run_adapter("resume-argv", "--json", request=RESUME_REQUEST)

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr, "brigade adapter resume-argv: the fake client adapter does not answer resume-argv\n"
        )

    def test_should_name_the_key_a_request_lacks(self):
        # Arrange
        self.machine.write_configuration('client = "claude-code"\n')

        # Act
        completed = self.run_adapter(
            "launch-argv",
            "--json",
            request='{"schema_version": 1, "worktree": "/srv/b42", "brief": "Deliver the task B42."}',
        )

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, "brigade adapter launch-argv: the request on stdin: lacks the key role\n")

    def test_should_name_the_file_a_launch_request_lacks(self):
        # Arrange
        rows = [
            (
                (
                    '{"schema_version": 1, "worktree": "/srv/b42", "brief": "Deliver the task B42.", "role": {"name":'
                    ' "builder", "package": "AGENT builder", "package_file": "/state/brigade/runs/r1/role.md",'
                    ' "capabilities": ["read"], "reasoning": "standard", "budget": 75}}'
                ),
                "brigade adapter launch-argv: the request on stdin: lacks the key progress_file\n",
            ),
            (
                (
                    '{"schema_version": 1, "worktree": "/srv/b42", "brief": "Deliver the task B42.",'
                    ' "progress_file": "/state/brigade/runs/r1/progress.md", "role": {"name": "builder",'
                    ' "package": "AGENT builder", "capabilities": ["read"], "reasoning": "standard", "budget": 75}}'
                ),
                "brigade adapter launch-argv: the request on stdin: lacks the key role.package_file\n",
            ),
        ]
        for request, expected_refusal in rows:
            with self.subTest(expected_refusal=expected_refusal):
                # Arrange
                self.machine.write_configuration('client = "claude-code"\n')

                # Act
                completed = self.run_adapter("launch-argv", "--json", request=request)

                # Assert
                self.assertEqual((completed.returncode, completed.stderr), (1, expected_refusal))

    def test_should_name_the_session_a_launch_or_a_resume_request_lacks(self):
        # Arrange
        rows = [
            (
                "launch-argv",
                (
                    '{"schema_version": 1, "worktree": "/srv/b42", "brief": "Deliver the task B42.",'
                    ' "progress_file": "/state/brigade/runs/r1/progress.md", "role": {"name": "builder",'
                    ' "package": "AGENT builder", "package_file": "/state/brigade/runs/r1/role.md",'
                    ' "capabilities": ["read"], "reasoning": "standard", "budget": 75}}'
                ),
                "brigade adapter launch-argv: the request on stdin: lacks the key session_id\n",
            ),
            (
                "resume-argv",
                (
                    '{"schema_version": 1, "worktree": "/srv/b42", "brief": "Carry on.",'
                    ' "progress_file": "/state/brigade/runs/r1/progress.md", "role": {"name": "builder",'
                    ' "package": "AGENT builder", "package_file": "/state/brigade/runs/r1/role.md",'
                    ' "capabilities": ["read"], "reasoning": "standard", "budget": 75}}'
                ),
                "brigade adapter resume-argv: the request on stdin: lacks the key session_id\n",
            ),
        ]
        for operation, request, expected_refusal in rows:
            with self.subTest(operation=operation):
                # Arrange
                self.machine.write_configuration('client = "claude-code"\n')

                # Act
                completed = self.run_adapter(operation, "--json", request=request)

                # Assert
                self.assertEqual((completed.returncode, completed.stderr), (1, expected_refusal))

    def test_should_refuse_a_stop_instant_a_launch_or_a_resume_request_lacks_or_carries_as_no_text(self):
        # Arrange
        rows = [
            (
                "launch-argv",
                (
                    '{"schema_version": 1, "worktree": "/srv/b42", "brief": "Deliver the task B42.", "session_id":'
                    ' "s1", "progress_file": "/state/brigade/runs/r1/progress.md", "role": {"name": "builder",'
                    ' "package": "AGENT builder", "package_file": "/state/brigade/runs/r1/role.md",'
                    ' "capabilities": ["read"], "reasoning": "standard", "budget": 75}}'
                ),
                "brigade adapter launch-argv: the request on stdin: lacks the key stop_at\n",
            ),
            (
                "resume-argv",
                (
                    '{"schema_version": 1, "worktree": "/srv/b42", "brief": "Carry on.", "session_id": "s1",'
                    ' "progress_file": "/state/brigade/runs/r1/progress.md", "role": {"name": "builder",'
                    ' "package": "AGENT builder", "package_file": "/state/brigade/runs/r1/role.md",'
                    ' "capabilities": ["read"], "reasoning": "standard", "budget": 75}}'
                ),
                "brigade adapter resume-argv: the request on stdin: lacks the key stop_at\n",
            ),
            (
                "launch-argv",
                (
                    '{"schema_version": 1, "worktree": "/srv/b42", "brief": "Deliver the task B42.", "session_id":'
                    ' "s1", "stop_at": 1791451380, "progress_file": "/state/brigade/runs/r1/progress.md", "role":'
                    ' {"name": "builder", "package": "AGENT builder", "package_file": "/state/brigade/runs/r1/role.md",'
                    ' "capabilities": ["read"], "reasoning": "standard", "budget": 75}}'
                ),
                "brigade adapter launch-argv: the request on stdin: stop_at is an integer, not a string\n",
            ),
        ]
        for operation, request, expected_refusal in rows:
            with self.subTest(expected_refusal=expected_refusal):
                # Arrange
                self.machine.write_configuration('client = "claude-code"\n')

                # Act
                completed = self.run_adapter(operation, "--json", request=request)

                # Assert
                self.assertEqual((completed.returncode, completed.stderr), (1, expected_refusal))

    def test_should_refuse_an_invalid_request_before_reading_the_configuration(self):
        # Arrange
        request_lacking_its_role = '{"schema_version": 1, "worktree": "/srv/b42", "brief": "Deliver the task B42."}'

        # Act
        completed = self.run_adapter("launch-argv", "--json", request=request_lacking_its_role)

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(completed.stderr, "brigade adapter launch-argv: the request on stdin: lacks the key role\n")


class BrigadeAdapterOnAnUnexpectedErrorTest(AdapterTestCase):
    def test_should_exit_70_with_the_traceback(self):
        # Arrange
        (self.machine.corpus / "config.toml").mkdir(parents=True)

        # Act
        completed = self.run_adapter("probe", "--json")

        # Assert
        self.assertEqual(completed.returncode, 70)
        self.assertEqual(completed.stdout, "")
        self.assertIn("IsADirectoryError", completed.stderr)
