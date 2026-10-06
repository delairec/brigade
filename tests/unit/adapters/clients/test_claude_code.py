import tempfile
import unittest
from pathlib import Path

from brigade.adapters.clients.claude_code import answer
from brigade.errors import BrigadeError

LAUNCH_REQUEST = {
    "schema_version": 1,
    "worktree": "/srv/worktrees/b42",
    "brief": "Deliver the task B42.",
    "role": {
        "name": "bastien",
        "package": "AGENT bastien",
        "capabilities": ["read", "shell"],
        "reasoning": "standard",
        "budget": 75,
    },
    "reasoning_table": {},
    "settings": {},
    "home": "/home/ada",
}


def parse_claude_output(stdout: str, stderr: str = "", exit_code: int = 0) -> dict:
    return answer(
        "parse-result",
        {
            "schema_version": 1,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "reasoning_table": {},
            "settings": {},
            "home": "/home/ada",
        },
    )


class ClaudeCodeProbe(unittest.TestCase):
    def test_should_declare_every_operation_present(self):
        # Act
        probe = answer("probe", {"schema_version": 1, "reasoning_table": {}, "settings": {}, "home": "/home/ada"})

        # Assert
        self.assertEqual(
            probe,
            {
                "schema_version": 1,
                "client": "claude-code",
                "version_argv": ["claude", "--version"],
                "operations": ["probe", "launch", "result", "resume", "transcripts"],
                "features": ["step_count", "tool_grants", "reset_hour"],
                "models": {"deepest": "fable", "deep": "fable", "standard": "opus", "light": "sonnet"},
            },
        )

    def test_should_bind_the_model_of_the_reasoning_row_config_toml_sets(self):
        # Arrange
        standard_row_set = {"standard": {"model": "sonnet", "effort": "low"}}

        # Act
        probe = answer(
            "probe", {"schema_version": 1, "reasoning_table": standard_row_set, "settings": {}, "home": "/home/ada"}
        )

        # Assert
        self.assertEqual(
            probe["models"], {"deepest": "fable", "deep": "fable", "standard": "sonnet", "light": "sonnet"}
        )


class ClaudeCodeLaunch(unittest.TestCase):
    def test_should_translate_the_role_into_an_unattended_command_reading_the_brief(self):
        # Act
        launch = answer("launch-argv", LAUNCH_REQUEST)

        # Assert
        self.assertEqual(
            launch,
            {
                "schema_version": 1,
                "argv": [
                    "claude",
                    "--print",
                    "--output-format",
                    "json",
                    "--model",
                    "opus",
                    "--effort",
                    "high",
                    "--max-turns",
                    "94",
                    "--append-system-prompt",
                    "AGENT bastien",
                    "--allowedTools",
                    "Read,Glob,Grep,Bash",
                ],
                "environment": {},
                "stdin": "Deliver the task B42.",
            },
        )

    def test_should_map_each_reasoning_level_to_its_default_model_and_effort(self):
        rows = [
            ("deepest", ["--model", "fable", "--effort", "max"]),
            ("deep", ["--model", "fable", "--effort", "high"]),
            ("standard", ["--model", "opus", "--effort", "high"]),
            ("light", ["--model", "sonnet", "--effort", "medium"]),
        ]
        for level, expected_model_and_effort in rows:
            with self.subTest(level=level):
                # Arrange
                request = {**LAUNCH_REQUEST, "role": {**LAUNCH_REQUEST["role"], "reasoning": level}}

                # Act
                launch = answer("launch-argv", request)

                # Assert
                self.assertEqual(launch["argv"][4:8], expected_model_and_effort)

    def test_should_take_the_row_the_configuration_sets_for_a_level(self):
        # Arrange
        request = {**LAUNCH_REQUEST, "reasoning_table": {"standard": {"model": "sonnet", "effort": "low"}}}

        # Act
        launch = answer("launch-argv", request)

        # Assert
        self.assertEqual(launch["argv"][4:8], ["--model", "sonnet", "--effort", "low"])

    def test_should_grant_the_tools_of_each_capability(self):
        rows = [
            (["read"], "Read,Glob,Grep"),
            (["write"], "Edit,Write,NotebookEdit"),
            (["shell"], "Bash"),
            (["net"], "WebFetch,WebSearch"),
            (["read", "write", "shell", "net"], "Read,Glob,Grep,Edit,Write,NotebookEdit,Bash,WebFetch,WebSearch"),
        ]
        for capabilities, expected_tools in rows:
            with self.subTest(capabilities=capabilities):
                # Arrange
                request = {**LAUNCH_REQUEST, "role": {**LAUNCH_REQUEST["role"], "capabilities": capabilities}}

                # Act
                launch = answer("launch-argv", request)

                # Assert
                self.assertEqual(launch["argv"][-2:], ["--allowedTools", expected_tools])

    def test_should_cap_the_turns_at_the_budget_plus_a_quarter_rounded_up(self):
        rows = [(75, "94"), (40, "50"), (1, "2")]
        for budget, expected_max_turns in rows:
            with self.subTest(budget=budget):
                # Arrange
                request = {**LAUNCH_REQUEST, "role": {**LAUNCH_REQUEST["role"], "budget": budget}}

                # Act
                launch = answer("launch-argv", request)

                # Assert
                self.assertEqual(launch["argv"][8:10], ["--max-turns", expected_max_turns])


class ClaudeCodeResume(unittest.TestCase):
    def test_should_resume_the_session_by_its_id(self):
        # Arrange
        request = {**LAUNCH_REQUEST, "brief": "Carry on from the progress file.", "session_id": "ada28962"}

        # Act
        resume = answer("resume-argv", request)

        # Assert
        self.assertEqual(
            resume,
            {
                "schema_version": 1,
                "argv": [
                    "claude",
                    "--print",
                    "--output-format",
                    "json",
                    "--resume",
                    "ada28962",
                    "--model",
                    "opus",
                    "--effort",
                    "high",
                    "--max-turns",
                    "94",
                    "--append-system-prompt",
                    "AGENT bastien",
                    "--allowedTools",
                    "Read,Glob,Grep,Bash",
                ],
                "environment": {},
                "stdin": "Carry on from the progress file.",
            },
        )


class ClaudeCodeResult(unittest.TestCase):
    def test_should_normalise_a_successful_result(self):
        # Arrange
        stdout = (
            '{"type":"result","subtype":"success","is_error":false,"duration_ms":1369,"num_turns":1,"result":"ok",'
            '"session_id":"ada28962","total_cost_usd":0.035,"usage":{"input_tokens":9,"cache_creation_input_tokens":16778,'
            '"cache_read_input_tokens":13803,"output_tokens":55,"service_tier":"standard"}}'
        )

        # Act
        result = parse_claude_output(stdout)

        # Assert
        self.assertEqual(
            result,
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
                "session_id": "ada28962",
                "duration_ms": 1369,
                "error_class": None,
                "reset": None,
                "message": None,
            },
        )

    def test_should_classify_a_run_stopped_by_its_turn_cap(self):
        # Arrange
        stdout = (
            '{"type":"result","subtype":"error_max_turns","is_error":true,"duration_ms":600000,"num_turns":94,'
            '"session_id":"ada28962","usage":{"input_tokens":1,"cache_creation_input_tokens":2,'
            '"cache_read_input_tokens":3,"output_tokens":4}}'
        )

        # Act
        result = parse_claude_output(stdout, exit_code=1)

        # Assert
        self.assertEqual(
            result,
            {
                "schema_version": 1,
                "outcome": "failed",
                "steps": 94,
                "usage": {
                    "input_tokens": 1,
                    "output_tokens": 4,
                    "cache_creation_input_tokens": 2,
                    "cache_read_input_tokens": 3,
                },
                "session_id": "ada28962",
                "duration_ms": 600000,
                "error_class": "turn_limit",
                "reset": None,
                "message": None,
            },
        )

    def test_should_classify_a_rate_limit_and_parse_the_reset_hour_it_names(self):
        # Arrange
        stdout = (
            '{"type":"result","subtype":"success","is_error":true,"duration_ms":800,"num_turns":3,'
            '"result":"You\'ve hit your limit \\u00b7 resets 3pm (Europe/Paris)","session_id":"ada28962",'
            '"usage":{"input_tokens":1,"cache_creation_input_tokens":0,"cache_read_input_tokens":0,"output_tokens":0}}'
        )

        # Act
        result = parse_claude_output(stdout, exit_code=1)

        # Assert
        self.assertEqual(
            result,
            {
                "schema_version": 1,
                "outcome": "failed",
                "steps": 3,
                "usage": {
                    "input_tokens": 1,
                    "output_tokens": 0,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                },
                "session_id": "ada28962",
                "duration_ms": 800,
                "error_class": "rate_limit",
                "reset": {"hour": "15:00", "timezone": "Europe/Paris"},
                "message": "You've hit your limit · resets 3pm (Europe/Paris)",
            },
        )

    def test_should_read_the_reset_hour_in_each_form_a_limit_message_names_it(self):
        rows = [
            ("You've hit your limit · resets 3pm", {"hour": "15:00", "timezone": None}),
            ("5-hour limit reached ∙ resets 10:30am (UTC)", {"hour": "10:30", "timezone": "UTC"}),
            ("Usage limit reached, resets 12am", {"hour": "00:00", "timezone": None}),
            ("Usage limit reached, resets 12pm", {"hour": "12:00", "timezone": None}),
            ("Rate limit reached, resets at 14:00", {"hour": "14:00", "timezone": None}),
            ("Claude AI usage limit reached", None),
        ]
        for message, expected_reset in rows:
            with self.subTest(message=message):
                # Arrange
                stdout = (
                    '{"type":"result","subtype":"success","is_error":true,"duration_ms":800,"num_turns":1,'
                    f'"result":"{message}","session_id":"ada28962","usage":{{}}}}'
                )

                # Act
                result = parse_claude_output(stdout, exit_code=1)

                # Assert
                self.assertEqual((result["error_class"], result["reset"]), ("rate_limit", expected_reset))

    def test_should_classify_any_other_error_as_an_execution_failure(self):
        # Arrange
        stdout = (
            '{"type":"result","subtype":"error_during_execution","is_error":true,"duration_ms":5000,"num_turns":2,'
            '"session_id":"ada28962","usage":{"input_tokens":1,"cache_creation_input_tokens":0,'
            '"cache_read_input_tokens":0,"output_tokens":0}}'
        )

        # Act
        result = parse_claude_output(stdout, exit_code=1)

        # Assert
        self.assertEqual(
            result,
            {
                "schema_version": 1,
                "outcome": "failed",
                "steps": 2,
                "usage": {
                    "input_tokens": 1,
                    "output_tokens": 0,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                },
                "session_id": "ada28962",
                "duration_ms": 5000,
                "error_class": "execution",
                "reset": None,
                "message": None,
            },
        )

    def test_should_report_an_output_that_holds_no_result_object(self):
        # Arrange
        no_output = ""

        # Act
        result = parse_claude_output(no_output, stderr="Error: Invalid API key\n", exit_code=1)

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
                "error_class": "unreadable_output",
                "reset": None,
                "message": "Error: Invalid API key",
            },
        )


class ClaudeCodeTranscripts(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.home.cleanup()

    def test_should_answer_the_messages_of_the_session_file_of_the_worktree(self):
        # Arrange
        projects = Path(self.home.name) / ".claude" / "projects" / "-srv-work-trees-b42"
        projects.mkdir(parents=True)
        (projects / "ada28962.jsonl").write_text(
            '{"type":"queue-operation","operation":"enqueue","sessionId":"ada28962"}\n'
            '{"type":"user","timestamp":"2026-10-06T10:00:00.000Z","message":{"role":"user","content":"Deliver the task B42."}}\n'
            '{"type":"attachment","timestamp":"2026-10-06T10:00:01.000Z","attachment":{}}\n'
            '{"type":"assistant","timestamp":"2026-10-06T10:00:09.000Z","message":{"role":"assistant",'
            '"content":[{"type":"text","text":"Done."}]}}\n'
        )
        request = {
            "schema_version": 1,
            "session_id": "ada28962",
            "worktree": "/srv/work.trees/b42",
            "reasoning_table": {},
            "settings": {},
            "home": self.home.name,
        }

        # Act
        transcripts = answer("transcripts", request)

        # Assert
        self.assertEqual(
            transcripts,
            {
                "schema_version": 1,
                "messages": [
                    {"role": "user", "timestamp": "2026-10-06T10:00:00.000Z", "content": "Deliver the task B42."},
                    {
                        "role": "assistant",
                        "timestamp": "2026-10-06T10:00:09.000Z",
                        "content": [{"type": "text", "text": "Done."}],
                    },
                ],
            },
        )

    def test_should_refuse_a_session_with_no_file(self):
        # Arrange
        request = {
            "schema_version": 1,
            "session_id": "ada28962",
            "worktree": "/srv/b42",
            "reasoning_table": {},
            "settings": {},
            "home": self.home.name,
        }

        # Act
        with self.assertRaises(BrigadeError) as raised:
            answer("transcripts", request)

        # Assert
        self.assertEqual(
            str(raised.exception),
            f"no transcript of session ada28962 at {self.home.name}/.claude/projects/-srv-b42/ada28962.jsonl",
        )
