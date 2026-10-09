import tempfile
import unittest
from pathlib import Path

from brigade.adapters.clients.claude_code import answer
from brigade.errors import BrigadeError

LAUNCH_REQUEST = {
    "schema_version": 1,
    "worktree": "/srv/worktrees/b42",
    "brief": "Deliver the task B42.",
    "progress_file": "/state/brigade/runs/r1/progress.md",
    "role": {
        "name": "builder",
        "package": "AGENT builder",
        "package_file": "/state/brigade/runs/r1/role.md",
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


class ClaudeCodeProbeTest(unittest.TestCase):
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
                "operations": ["probe", "launch", "result", "resume", "transcripts", "actions"],
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


class ClaudeCodeLaunchTest(unittest.TestCase):
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
                    "stream-json",
                    "--verbose",
                    "--permission-mode",
                    "dontAsk",
                    "--model",
                    "opus",
                    "--effort",
                    "high",
                    "--max-turns",
                    "94",
                    "--append-system-prompt-file",
                    "/state/brigade/runs/r1/role.md",
                    "--allowedTools",
                    "Read,Glob,Grep,Bash,Write(//state/brigade/runs/r1/progress.md),Edit(//state/brigade/runs/r1/progress.md)",
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
                self.assertEqual(launch["argv"][7:11], expected_model_and_effort)

    def test_should_take_the_row_the_configuration_sets_for_a_level(self):
        # Arrange
        request = {**LAUNCH_REQUEST, "reasoning_table": {"standard": {"model": "sonnet", "effort": "low"}}}

        # Act
        launch = answer("launch-argv", request)

        # Assert
        self.assertEqual(launch["argv"][7:11], ["--model", "sonnet", "--effort", "low"])

    def test_should_grant_the_tools_of_each_capability(self):
        rows = [
            (
                ["read"],
                ("Read,Glob,Grep,Write(//state/brigade/runs/r1/progress.md),Edit(//state/brigade/runs/r1/progress.md)"),
            ),
            (
                ["write"],
                (
                    "Edit,Write,NotebookEdit,"
                    "Write(//state/brigade/runs/r1/progress.md),Edit(//state/brigade/runs/r1/progress.md)"
                ),
            ),
            (
                ["shell"],
                ("Bash,Write(//state/brigade/runs/r1/progress.md),Edit(//state/brigade/runs/r1/progress.md)"),
            ),
            (
                ["net"],
                (
                    "WebFetch,WebSearch,"
                    "Write(//state/brigade/runs/r1/progress.md),Edit(//state/brigade/runs/r1/progress.md)"
                ),
            ),
            (
                ["read", "write", "shell", "net"],
                (
                    "Read,Glob,Grep,Edit,Write,NotebookEdit,Bash,WebFetch,WebSearch,"
                    "Write(//state/brigade/runs/r1/progress.md),Edit(//state/brigade/runs/r1/progress.md)"
                ),
            ),
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
                self.assertEqual(launch["argv"][11:13], ["--max-turns", expected_max_turns])


class ClaudeCodeResumeTest(unittest.TestCase):
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
                    "stream-json",
                    "--verbose",
                    "--permission-mode",
                    "dontAsk",
                    "--resume",
                    "ada28962",
                    "--model",
                    "opus",
                    "--effort",
                    "high",
                    "--max-turns",
                    "94",
                    "--append-system-prompt-file",
                    "/state/brigade/runs/r1/role.md",
                    "--allowedTools",
                    "Read,Glob,Grep,Bash,Write(//state/brigade/runs/r1/progress.md),Edit(//state/brigade/runs/r1/progress.md)",
                ],
                "environment": {},
                "stdin": "Carry on from the progress file.",
            },
        )


class ClaudeCodeResultTest(unittest.TestCase):
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

    def test_should_report_a_json_document_that_is_not_the_result_object(self):
        # Arrange
        system_message = '{"type": "system", "subtype": "init", "session_id": "s-42"}'

        # Act
        result = parse_claude_output(system_message, stderr="Error: interrupted\n", exit_code=1)

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
                "message": "Error: interrupted",
            },
        )

    def test_should_read_the_result_event_that_ends_a_stream(self):
        # Arrange
        stream = (
            '{"type":"system","subtype":"init","session_id":"ada28962"}\n'
            '{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"Done."}]}}\n'
            '{"type":"result","subtype":"success","is_error":false,"duration_ms":1369,"num_turns":3,"result":"Done.",'
            '"session_id":"ada28962","usage":{"input_tokens":9,"cache_creation_input_tokens":16778,'
            '"cache_read_input_tokens":13803,"output_tokens":55}}\n'
        )

        # Act
        result = parse_claude_output(stream)

        # Assert
        self.assertEqual(
            result,
            {
                "schema_version": 1,
                "outcome": "done",
                "steps": 3,
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

    def test_should_read_the_last_of_two_result_events(self):
        # Arrange
        stream = (
            '{"type":"result","subtype":"error_during_execution","is_error":true,"num_turns":2,"session_id":"s1"}\n'
            '{"type":"result","subtype":"success","is_error":false,"num_turns":5,"session_id":"s1"}\n'
        )

        # Act
        result = parse_claude_output(stream)

        # Assert
        self.assertEqual((result["outcome"], result["steps"]), ("done", 5))

    def test_should_report_a_stream_that_holds_no_result_event(self):
        # Arrange
        stream = (
            '{"type":"system","subtype":"init","session_id":"ada28962"}\n'
            '{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"Reading."}]}}\n'
        )

        # Act
        result = parse_claude_output(stream, stderr="Error: interrupted\n", exit_code=1)

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
                "message": "Error: interrupted",
            },
        )

    def test_should_report_no_usage_when_the_result_object_carries_none(self):
        # Arrange
        result_without_usage = (
            '{"type": "result", "subtype": "success", "is_error": false, "num_turns": 3, "session_id": "s-42",'
            ' "duration_ms": 9000, "result": "Done.", "usage": null}'
        )

        # Act
        result = parse_claude_output(result_without_usage)

        # Assert
        self.assertEqual(
            result,
            {
                "schema_version": 1,
                "outcome": "done",
                "steps": 3,
                "usage": None,
                "session_id": "s-42",
                "duration_ms": 9000,
                "error_class": None,
                "reset": None,
                "message": None,
            },
        )


def read_claude_actions(output: str) -> dict:
    return answer(
        "actions",
        {"schema_version": 1, "output": output, "reasoning_table": {}, "settings": {}, "home": "/home/ada"},
    )


class ClaudeCodeActionsTest(unittest.TestCase):
    def test_should_name_each_tool_call_by_the_argument_that_identifies_it(self):
        rows = [
            (
                "a path",
                '{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","id":"t1",'
                '"name":"Read","input":{"file_path":"/srv/b42/README.md","limit":40}}]}}\n',
                "Read /srv/b42/README.md",
            ),
            (
                "a command",
                '{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","id":"t1",'
                '"name":"Bash","input":{"command":"python3 -m unittest","timeout":600}}]}}\n',
                "Bash python3 -m unittest",
            ),
            (
                "a pattern",
                '{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","id":"t1",'
                '"name":"Grep","input":{"pattern":"def answer","path":"brigade"}}]}}\n',
                "Grep def answer",
            ),
            (
                "no argument",
                '{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","id":"t1",'
                '"name":"TodoWrite","input":{"todos":[]}}]}}\n',
                "TodoWrite",
            ),
        ]
        for case, event, expected_summary in rows:
            with self.subTest(case=case):
                # Act
                actions = read_claude_actions(event)

                # Assert
                self.assertEqual(
                    actions, {"schema_version": 1, "actions": [{"kind": "tool", "summary": expected_summary}]}
                )

    def test_should_give_the_first_line_of_a_text(self):
        # Arrange
        event = (
            '{"type":"assistant","message":{"role":"assistant","content":'
            '[{"type":"text","text":"I read the task first.\\nThen I write the test."}]}}\n'
        )

        # Act
        actions = read_claude_actions(event)

        # Assert
        self.assertEqual(
            actions, {"schema_version": 1, "actions": [{"kind": "text", "summary": "I read the task first."}]}
        )

    def test_should_give_the_outcome_of_the_segment_for_the_result_event(self):
        rows = [
            ("done", '{"type":"result","subtype":"success","is_error":false,"num_turns":3}\n', "done"),
            ("failed", '{"type":"result","subtype":"error_max_turns","is_error":true,"num_turns":94}\n', "failed"),
        ]
        for case, event, expected_summary in rows:
            with self.subTest(case=case):
                # Act
                actions = read_claude_actions(event)

                # Assert
                self.assertEqual(
                    actions, {"schema_version": 1, "actions": [{"kind": "result", "summary": expected_summary}]}
                )

    def test_should_read_the_actions_of_every_event_in_order_and_skip_the_others(self):
        # Arrange
        output = (
            '{"type":"system","subtype":"init","session_id":"ada28962"}\n'
            '{"type":"assistant","message":{"role":"assistant","content":[{"type":"thinking","thinking":"Plan."},'
            '{"type":"text","text":"Reading."},{"type":"tool_use","id":"t1","name":"Glob","input":{"pattern":"*.py"}}]}}\n'
            '{"type":"user","message":{"role":"user","content":[{"type":"tool_result","tool_use_id":"t1","content":"a.py"}]}}\n'
            "not a json line\n"
            "[]\n"
        )

        # Act
        actions = read_claude_actions(output)

        # Assert
        self.assertEqual(
            actions,
            {
                "schema_version": 1,
                "actions": [{"kind": "text", "summary": "Reading."}, {"kind": "tool", "summary": "Glob *.py"}],
            },
        )


class ClaudeCodeUnsupportedOperationTest(unittest.TestCase):
    def test_should_refuse_an_operation_it_does_not_answer(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            answer("compact", {"schema_version": 1})

        # Assert
        self.assertEqual(str(refusal.exception), "the claude-code client adapter does not answer compact")


class ClaudeCodeTranscriptsTest(unittest.TestCase):
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
