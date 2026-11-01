import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.adapters.clients.vibe import answer
from brigade.errors import BrigadeError

FIXTURES = Path(__file__).parent / "fixtures" / "vibe"
DONE_SESSION = "07c22c12-2a67-4c18-3dfa-fb6379155664"
CUT_SESSION = "50627de2-dcf5-d0d0-0d79-a612bb6f5ae8"


def create_launch_request(package_file: Path, capabilities: list[str], reasoning_table: dict) -> dict:
    return {
        "schema_version": 1,
        "worktree": "/srv/worktrees/b42",
        "brief": "Deliver the task B42.",
        "progress_file": "/state/brigade/runs/r1/progress.md",
        "session_id": "6f1c2a9e-3b7d-4e21-9a55-0c8d4b7e2f13",
        "stop_at": None,
        "role": {
            "name": "builder",
            "package": "AGENT builder",
            "package_file": str(package_file),
            "capabilities": capabilities,
            "reasoning": "standard",
            "budget": 75,
        },
        "reasoning_table": reasoning_table,
        "settings": {},
        "home": "/srv/homes/ada",
    }


def parse_vibe_output(stdout: str, stderr: str, exit_code: int, home: str) -> dict:
    return answer(
        "parse-result",
        {
            "schema_version": 1,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "reasoning_table": {},
            "settings": {},
            "home": home,
        },
    )


def read_vibe_transcripts(session_id: str, home: str) -> dict:
    return answer(
        "transcripts",
        {
            "schema_version": 1,
            "session_id": session_id,
            "worktree": "/srv/worktrees/b42",
            "reasoning_table": {},
            "settings": {},
            "home": home,
        },
    )


class VibeHomeTestCase(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.TemporaryDirectory()
        self.sessions = Path(self.home.name) / ".vibe" / "logs" / "session" / "unified"

    def tearDown(self):
        self.home.cleanup()

    def install_captured_session(self, session_id: str) -> None:
        shutil.copytree(FIXTURES / "session-store" / session_id, self.sessions / session_id)


class VibeProbeTest(unittest.TestCase):
    def test_should_declare_the_operations_and_the_features_of_vibe(self):
        # Act
        probe = answer("probe", {"schema_version": 1, "reasoning_table": {}, "settings": {}, "home": "/srv/homes/ada"})

        # Assert
        self.assertEqual(
            probe,
            {
                "schema_version": 1,
                "client": "vibe",
                "version_argv": ["vibe", "--version"],
                "operations": ["probe", "launch", "result", "transcripts"],
                "features": ["step_count", "tool_grants"],
                "models": {
                    "deepest": "mistral-medium-3.5",
                    "deep": "mistral-medium-3.5",
                    "standard": "mistral-medium-3.5",
                    "light": "mistral-medium-3.5",
                },
            },
        )

    def test_should_bind_the_model_of_the_reasoning_row_config_toml_sets(self):
        # Arrange
        deep_row_set = {"deep": {"model": "mistral-large", "effort": "high"}}

        # Act
        probe = answer(
            "probe", {"schema_version": 1, "reasoning_table": deep_row_set, "settings": {}, "home": "/srv/homes/ada"}
        )

        # Assert
        self.assertEqual(
            probe["models"],
            {
                "deepest": "mistral-medium-3.5",
                "deep": "mistral-large",
                "standard": "mistral-medium-3.5",
                "light": "mistral-medium-3.5",
            },
        )


class VibeLaunchTest(unittest.TestCase):
    def setUp(self):
        self.run_directory = tempfile.TemporaryDirectory()
        self.package_file = Path(self.run_directory.name) / "role.md"
        self.package_file.write_text("You are the builder.\n", encoding="utf-8")

    def tearDown(self):
        self.run_directory.cleanup()

    def test_should_translate_the_role_into_an_unattended_command_reading_the_package_then_the_brief(self):
        # Arrange
        no_reasoning_row = {}
        request = create_launch_request(self.package_file, ["read", "shell"], no_reasoning_row)

        # Act
        launch = answer("launch-argv", request)

        # Assert
        self.assertEqual(
            launch,
            {
                "schema_version": 1,
                "argv": [
                    "vibe",
                    "-p",
                    "--output",
                    "streaming",
                    "--trust",
                    "--auto-approve",
                    "--max-turns",
                    "94",
                    "--enabled-tools",
                    "read_file",
                    "--enabled-tools",
                    "grep",
                    "--enabled-tools",
                    "bash",
                    "--enabled-tools",
                    "write_file",
                ],
                "environment": {"VIBE_CLI": "rust", "VIBE_ACTIVE_MODEL": "mistral-medium-3.5"},
                "stdin": "You are the builder.\n\n---\nDeliver the task B42.",
                "session_id": None,
            },
        )

    def test_should_grant_the_tools_of_each_capability_and_write_file_for_the_progress_file(self):
        # Arrange
        rows = [
            (
                ["read"],
                [
                    "vibe",
                    "-p",
                    "--output",
                    "streaming",
                    "--trust",
                    "--auto-approve",
                    "--max-turns",
                    "94",
                    "--enabled-tools",
                    "read_file",
                    "--enabled-tools",
                    "grep",
                    "--enabled-tools",
                    "write_file",
                ],
            ),
            (
                ["write"],
                [
                    "vibe",
                    "-p",
                    "--output",
                    "streaming",
                    "--trust",
                    "--auto-approve",
                    "--max-turns",
                    "94",
                    "--enabled-tools",
                    "edit",
                    "--enabled-tools",
                    "write_file",
                ],
            ),
            (
                ["shell"],
                [
                    "vibe",
                    "-p",
                    "--output",
                    "streaming",
                    "--trust",
                    "--auto-approve",
                    "--max-turns",
                    "94",
                    "--enabled-tools",
                    "bash",
                    "--enabled-tools",
                    "write_file",
                ],
            ),
            (
                ["net"],
                [
                    "vibe",
                    "-p",
                    "--output",
                    "streaming",
                    "--trust",
                    "--auto-approve",
                    "--max-turns",
                    "94",
                    "--enabled-tools",
                    "web_fetch",
                    "--enabled-tools",
                    "web_search",
                    "--enabled-tools",
                    "write_file",
                ],
            ),
            (
                [],
                [
                    "vibe",
                    "-p",
                    "--output",
                    "streaming",
                    "--trust",
                    "--auto-approve",
                    "--max-turns",
                    "94",
                    "--enabled-tools",
                    "write_file",
                ],
            ),
        ]
        for capabilities, expected_argv in rows:
            with self.subTest(capabilities=capabilities):
                request = create_launch_request(self.package_file, capabilities, {})

                # Act
                launch = answer("launch-argv", request)

                # Assert
                self.assertEqual(launch["argv"], expected_argv)

    def test_should_activate_the_model_of_the_row_config_toml_sets_for_the_level_of_the_role(self):
        # Arrange
        standard_row_set = {"standard": {"model": "mistral-large", "effort": "high"}}
        request = create_launch_request(self.package_file, ["read"], standard_row_set)

        # Act
        launch = answer("launch-argv", request)

        # Assert
        self.assertEqual(launch["environment"], {"VIBE_CLI": "rust", "VIBE_ACTIVE_MODEL": "mistral-large"})


class VibeResultTest(VibeHomeTestCase):
    def test_should_read_a_session_ended_by_its_final_message_and_its_usage_from_the_store(self):
        # Arrange
        self.install_captured_session(DONE_SESSION)
        stdout = (FIXTURES / "streams" / "done.jsonl").read_text(encoding="utf-8")

        # Act
        result = parse_vibe_output(stdout, "", 0, self.home.name)

        # Assert
        self.assertEqual(
            result,
            {
                "schema_version": 1,
                "outcome": "done",
                "steps": 1,
                "usage": {
                    "input_tokens": 21086,
                    "output_tokens": 212,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 11520,
                },
                "session_id": "07c22c12-2a67-4c18-3dfa-fb6379155664",
                "duration_ms": 3667,
                "cost_usd": None,
                "error_class": None,
                "reset": None,
                "message": None,
            },
        )

    def test_should_leave_the_usage_null_when_the_session_store_cannot_be_read(self):
        # Arrange
        stdout = (
            '{"id":"a1","sessionId":"s1","type":"message","role":"assistant",'
            '"content":[{"type":"text","text":"seven\\nbrigade-end: done"}],"createdAt":1000,"updatedAt":1500}\n'
        )
        session = self.sessions / "s1"
        generation = session / "generations" / "0000000000000001"
        generation.mkdir(parents=True)
        rows = [
            ("a CURRENT that is no JSON", "0000000000000001", "{}"),
            ("a CURRENT naming no generation", "{}", "{}"),
            ("a generation that is missing", '{"generation":"0000000000000002"}', "{}"),
            (
                "a session with no token usage",
                '{"generation":"0000000000000001"}',
                '{"snapshot":{"session":{"tokenUsage":null}}}',
            ),
        ]
        for store, current, projection_state in rows:
            with self.subTest(store=store):
                (session / "CURRENT").write_text(current, encoding="utf-8")
                (generation / "projection-state.json").write_text(projection_state, encoding="utf-8")

                # Act
                result = parse_vibe_output(stdout, "", 0, self.home.name)

                # Assert
                self.assertIsNone(result["usage"])

    def test_should_read_a_run_cut_by_its_turn_cap(self):
        # Arrange
        stdout = (FIXTURES / "streams" / "cut.jsonl").read_text(encoding="utf-8")
        stderr = "The configured conversation limit was reached\n"

        # Act
        result = parse_vibe_output(stdout, stderr, 1, self.home.name)

        # Assert
        self.assertEqual(
            result,
            {
                "schema_version": 1,
                "outcome": "failed",
                "steps": 0,
                "usage": None,
                "session_id": "50627de2-dcf5-d0d0-0d79-a612bb6f5ae8",
                "duration_ms": 2661,
                "cost_usd": None,
                "error_class": "turn_limit",
                "reset": None,
                "message": "The configured conversation limit was reached",
            },
        )

    def test_should_classify_a_failure_by_the_last_line_of_stderr(self):
        # Arrange
        no_entry = ""
        ended_on_a_message = (FIXTURES / "streams" / "done.jsonl").read_text(encoding="utf-8")
        ended_on_an_effect = (FIXTURES / "streams" / "cut.jsonl").read_text(encoding="utf-8")
        rows = [
            (no_entry, 1, "Error: Rate limit exceeded (429)\n", "rate_limit", "Error: Rate limit exceeded (429)"),
            (ended_on_a_message, 1, "Error: session/start\n", "execution", "Error: session/start"),
            (ended_on_an_effect, 2, "", "unreadable_output", None),
        ]
        for stdout, exit_code, stderr, expected_error_class, expected_message in rows:
            with self.subTest(expected_error_class=expected_error_class):
                # Act
                result = parse_vibe_output(stdout, stderr, exit_code, self.home.name)

                # Assert
                self.assertEqual(
                    result,
                    {
                        "schema_version": 1,
                        "outcome": "failed",
                        "steps": None,
                        "usage": None,
                        "session_id": None,
                        "duration_ms": None,
                        "cost_usd": None,
                        "error_class": expected_error_class,
                        "reset": None,
                        "message": expected_message,
                    },
                )

    def test_should_report_an_output_whose_line_is_no_json_object(self):
        # Arrange
        rows = ["Error: session/start\n", '["message"]\n']
        for stdout in rows:
            with self.subTest(stdout=stdout):
                # Act
                result = parse_vibe_output(stdout, "Error: session/start\n", 0, self.home.name)

                # Assert
                self.assertEqual(result["error_class"], "unreadable_output")

    def test_should_report_an_output_that_holds_no_entry(self):
        # Arrange
        empty_stdout = ""

        # Act
        result = parse_vibe_output(empty_stdout, "", 0, self.home.name)

        # Assert
        self.assertEqual(result["error_class"], "unreadable_output")


class VibeEndDeclarationTest(VibeHomeTestCase):
    def test_should_read_the_end_declared_on_the_last_line_of_the_final_message(self):
        # Arrange
        rows = [
            (
                (
                    '{"id":"a1","sessionId":"s1","type":"message","role":"assistant",'
                    '"content":[{"type":"text","text":"seven\\nbrigade-end: handed_over"}],'
                    '"createdAt":1000,"updatedAt":1500}\n'
                ),
                "handed_over",
                None,
            ),
            (
                (
                    '{"id":"a1","sessionId":"s1","type":"message","role":"assistant",'
                    '"content":[{"type":"text","text":"Which base?\\nbrigade-end: blocked"}],'
                    '"createdAt":1000,"updatedAt":1500}\n'
                ),
                "blocked",
                "Which base?\nbrigade-end: blocked",
            ),
            (
                (
                    '{"id":"a1","sessionId":"s1","type":"message","role":"assistant",'
                    '"content":[{"type":"text","text":"seven"}],"createdAt":1000,"updatedAt":1500}\n'
                ),
                "undeclared",
                None,
            ),
        ]
        for stdout, expected_outcome, expected_message in rows:
            with self.subTest(expected_outcome=expected_outcome):
                # Act
                result = parse_vibe_output(stdout, "", 0, self.home.name)

                # Assert
                self.assertEqual(result["outcome"], expected_outcome)
                self.assertEqual(result["message"], expected_message)

    def test_should_read_a_stream_ending_on_another_entry_as_undeclared(self):
        # Arrange
        stdout = (
            '{"id":"a1","sessionId":"s1","type":"message","role":"assistant",'
            '"content":[{"type":"text","text":"seven\\nbrigade-end: done"}],"createdAt":1000,"updatedAt":1500}\n'
            '{"id":"r1","sessionId":"s1","type":"reasoning","text":"Done.","createdAt":1600,"updatedAt":1700}\n'
        )

        # Act
        result = parse_vibe_output(stdout, "", 0, self.home.name)

        # Assert
        self.assertEqual(result["outcome"], "undeclared")

    def test_should_count_and_read_the_messages_of_the_model_and_none_of_its_other_entries(self):
        # Arrange
        stdout = (
            '{"id":"a1","sessionId":"s1","type":"message","role":"assistant",'
            '"content":[{"type":"text","text":"seven"}],"createdAt":1000,"updatedAt":1500}\n'
            '{"id":"e1","sessionId":"s1","type":"effect","role":"assistant",'
            '"content":[{"type":"text","text":"brigade-end: done"}],"createdAt":1600,"updatedAt":1700}\n'
        )

        # Act
        result = parse_vibe_output(stdout, "", 0, self.home.name)

        # Assert
        self.assertEqual(result["outcome"], "undeclared")
        self.assertEqual(result["steps"], 1)


class VibeTranscriptsTest(VibeHomeTestCase):
    def test_should_answer_the_messages_of_the_session_from_its_journal(self):
        # Arrange
        self.install_captured_session(CUT_SESSION)

        # Act
        transcripts = read_vibe_transcripts(CUT_SESSION, self.home.name)

        # Assert
        self.assertEqual(
            transcripts,
            {
                "schema_version": 1,
                "messages": [
                    {
                        "role": "user",
                        "timestamp": None,
                        "content": [
                            {
                                "text": "Read the file notes.txt with read_file, then write its hour into hour.txt"
                                " with write_file, then answer with the hour.",
                                "type": "text",
                            }
                        ],
                        "tool_calls": 0,
                        "id": None,
                        "usage": None,
                    },
                    {
                        "role": "assistant",
                        "timestamp": None,
                        "content": "",
                        "tool_calls": 1,
                        "id": None,
                        "usage": {
                            "input_tokens": 10703,
                            "output_tokens": 68,
                            "cache_creation_input_tokens": 0,
                            "cache_read_input_tokens": 512,
                        },
                    },
                ],
                "subagents": [],
            },
        )

    def test_should_answer_each_turn_of_the_model_once_with_its_text(self):
        # Arrange
        self.install_captured_session(DONE_SESSION)

        # Act
        transcripts = read_vibe_transcripts(DONE_SESSION, self.home.name)

        # Assert
        self.assertEqual(
            transcripts["messages"],
            [
                {
                    "role": "user",
                    "timestamp": None,
                    "content": [
                        {
                            "text": "Now write that hour in digits. Answer in two lines: the hour in digits on the first"
                            " line, and the text brigade-end: done alone on the second line.",
                            "type": "text",
                        }
                    ],
                    "tool_calls": 0,
                    "id": None,
                    "usage": None,
                },
                {
                    "role": "assistant",
                    "timestamp": None,
                    "content": "7\nbrigade-end: done",
                    "tool_calls": 0,
                    "id": None,
                    "usage": {
                        "input_tokens": 11006,
                        "output_tokens": 45,
                        "cache_creation_input_tokens": 0,
                        "cache_read_input_tokens": 512,
                    },
                },
            ],
        )

    def test_should_read_the_journal_in_the_order_of_its_sequences(self):
        # Arrange
        journal = self.sessions / "s1" / "journal"
        journal.mkdir(parents=True)
        (journal / "0000000000000002.jsonl").write_text(
            '{"type":"projection_delta","payload":{"delta":[{"op":"append_entry",'
            '"entry":{"role":"user","content":[{"type":"text","text":"First."}]}}]}}\n',
            encoding="utf-8",
        )
        (journal / "0000000000000010.jsonl").write_text(
            '{"type":"projection_delta","payload":{"delta":[{"op":"append_entry",'
            '"entry":{"role":"user","content":[{"type":"text","text":"Second."}]}}]}}\n',
            encoding="utf-8",
        )

        # Act
        transcripts = read_vibe_transcripts("s1", self.home.name)

        # Assert
        self.assertEqual(
            transcripts["messages"],
            [
                {
                    "role": "user",
                    "timestamp": None,
                    "content": [{"type": "text", "text": "First."}],
                    "tool_calls": 0,
                    "id": None,
                    "usage": None,
                },
                {
                    "role": "user",
                    "timestamp": None,
                    "content": [{"type": "text", "text": "Second."}],
                    "tool_calls": 0,
                    "id": None,
                    "usage": None,
                },
            ],
        )

    def test_should_name_the_path_of_a_missing_journal(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            read_vibe_transcripts("s1", self.home.name)

        # Assert
        self.assertEqual(str(raised.exception), f"no journal of session s1 at {self.sessions}/s1/journal")

    def test_should_name_the_path_of_a_journal_it_cannot_read(self):
        # Arrange
        journal = self.sessions / "s1" / "journal"
        journal.mkdir(parents=True)
        (journal / "0000000000000001.jsonl").write_text('{"type":"projection_delta"\n', encoding="utf-8")

        # Act
        with self.assertRaises(BrigadeError) as raised:
            read_vibe_transcripts("s1", self.home.name)

        # Assert
        self.assertRegex(str(raised.exception), f"^unreadable journal at {journal}/0000000000000001.jsonl: ")

    def test_should_name_the_path_of_a_journal_file_it_cannot_open(self):
        # Arrange
        journal = self.sessions / "s1" / "journal"
        (journal / "0000000000000001.jsonl").mkdir(parents=True)

        # Act
        with self.assertRaises(BrigadeError) as raised:
            read_vibe_transcripts("s1", self.home.name)

        # Assert
        self.assertRegex(str(raised.exception), f"^unreadable journal at {journal}/0000000000000001.jsonl: ")


class VibeUnsupportedOperationTest(unittest.TestCase):
    def test_should_refuse_the_operations_vibe_does_not_answer(self):
        # Arrange
        rows = [
            ("resume-argv", "the vibe client adapter does not answer resume-argv"),
            ("actions", "the vibe client adapter does not answer actions"),
        ]
        for operation, expected_error in rows:
            with self.subTest(operation=operation):
                # Act
                with self.assertRaises(BrigadeError) as raised:
                    answer(operation, {"schema_version": 1})

                # Assert
                self.assertEqual(str(raised.exception), expected_error)
