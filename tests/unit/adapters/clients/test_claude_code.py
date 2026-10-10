import tempfile
import unittest
from pathlib import Path

from brigade.adapters.clients.claude_code import answer
from brigade.errors import BrigadeError

FIXTURES = Path(__file__).parent / "fixtures" / "claude-code"
CLI_FIXTURES = Path(__file__).parents[3] / "cli" / "fixtures" / "claude-code"

LAUNCH_REQUEST = {
    "schema_version": 1,
    "worktree": "/srv/worktrees/b42",
    "brief": "Deliver the task B42.",
    "progress_file": "/state/brigade/runs/r1/progress.md",
    "session_id": "6f1c2a9e-3b7d-4e21-9a55-0c8d4b7e2f13",
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
                    "--session-id",
                    "6f1c2a9e-3b7d-4e21-9a55-0c8d4b7e2f13",
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
                "session_id": "6f1c2a9e-3b7d-4e21-9a55-0c8d4b7e2f13",
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
                self.assertEqual(launch["argv"][9:13], expected_model_and_effort)

    def test_should_take_the_row_the_configuration_sets_for_a_level(self):
        # Arrange
        request = {**LAUNCH_REQUEST, "reasoning_table": {"standard": {"model": "sonnet", "effort": "low"}}}

        # Act
        launch = answer("launch-argv", request)

        # Assert
        self.assertEqual(launch["argv"][9:13], ["--model", "sonnet", "--effort", "low"])

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
                self.assertEqual(launch["argv"][13:15], ["--max-turns", expected_max_turns])


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
                "session_id": "ada28962",
            },
        )


class ClaudeCodeResultTest(unittest.TestCase):
    def test_should_normalise_a_successful_result(self):
        # Arrange
        stdout = (
            '{"type":"result","subtype":"success","is_error":false,"duration_ms":1369,"num_turns":1,'
            '"result":"Delivered.\\nbrigade-end: done",'
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
                "cost_usd": 0.035,
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
                "cost_usd": None,
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
                "cost_usd": None,
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
                "cost_usd": None,
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
                "cost_usd": None,
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
                "cost_usd": None,
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
            '{"type":"result","subtype":"success","is_error":false,"duration_ms":1369,"num_turns":3,'
            '"result":"Done.\\nbrigade-end: done",'
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
                "cost_usd": None,
                "error_class": None,
                "reset": None,
                "message": None,
            },
        )

    def test_should_read_the_last_of_two_result_events(self):
        # Arrange
        stream = (
            '{"type":"result","subtype":"error_during_execution","is_error":true,"num_turns":2,"session_id":"s1"}\n'
            '{"type":"result","subtype":"success","is_error":false,"num_turns":5,"result":"brigade-end: done",'
            '"session_id":"s1"}\n'
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
                "cost_usd": None,
                "error_class": "unreadable_output",
                "reset": None,
                "message": "Error: interrupted",
            },
        )

    def test_should_sum_the_usage_of_every_model_the_session_used(self):
        # Arrange
        stdout = (
            '{"type":"result","subtype":"success","is_error":false,"duration_ms":1369,"num_turns":4,"result":"ok",'
            '"session_id":"s-42","usage":{"input_tokens":1,"cache_creation_input_tokens":2,'
            '"cache_read_input_tokens":3,"output_tokens":4},'
            '"modelUsage":{"claude-opus-5-5":{"inputTokens":100,"outputTokens":2000,"cacheReadInputTokens":30000,'
            '"cacheCreationInputTokens":4000,"costUSD":1.5},"claude-haiku-5-5":{"inputTokens":10,"outputTokens":200,'
            '"cacheReadInputTokens":3000,"cacheCreationInputTokens":400,"costUSD":0.1}}}'
        )

        # Act
        result = parse_claude_output(stdout)

        # Assert
        self.assertEqual(
            result["usage"],
            {
                "input_tokens": 110,
                "output_tokens": 2200,
                "cache_creation_input_tokens": 4400,
                "cache_read_input_tokens": 33000,
            },
        )

    def test_should_report_the_usage_and_the_cost_of_the_whole_session_of_run_2ee96f(self):
        # Arrange
        stdout = (CLI_FIXTURES / "result-after-task-notification.json").read_text()

        # Act
        result = parse_claude_output(stdout)

        # Assert
        self.assertEqual(
            result,
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

    def test_should_count_no_steps_for_a_result_that_follows_a_task_notification(self):
        # Arrange
        stdout = (
            '{"type":"result","subtype":"success","is_error":false,"duration_ms":19091,"num_turns":2,"result":"ok",'
            '"session_id":"s-42","origin":{"kind":"task-notification","producer":"session-task"}}'
        )

        # Act
        result = parse_claude_output(stdout)

        # Assert
        self.assertIsNone(result["steps"])

    def test_should_count_the_turns_of_a_result_that_answers_the_brief(self):
        # Arrange
        stdout = (
            '{"type":"result","subtype":"success","is_error":false,"duration_ms":19091,"num_turns":52,"result":"ok",'
            '"session_id":"s-42","origin":{"kind":"user"}}'
        )

        # Act
        result = parse_claude_output(stdout)

        # Assert
        self.assertEqual(result["steps"], 52)

    def test_should_report_no_usage_when_the_result_object_carries_none(self):
        # Arrange
        result_without_usage = (
            '{"type": "result", "subtype": "success", "is_error": false, "num_turns": 3, "session_id": "s-42",'
            ' "duration_ms": 9000, "result": "Done.\\nbrigade-end: done", "usage": null}'
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
                "cost_usd": None,
                "error_class": None,
                "reset": None,
                "message": None,
            },
        )


class ClaudeCodeEndDeclarationTest(unittest.TestCase):
    def test_should_answer_the_outcome_the_last_line_of_the_final_message_declares(self):
        rows = [
            ("done", "Pull request #96 is open.\\nbrigade-end: done", "done"),
            ("handed over", "Progress written.\\nbrigade-end: handed_over", "handed_over"),
            ("blocked", "The ruling is the user's.\\nbrigade-end: blocked", "blocked"),
            ("a line break after the declaration", "Pull request #96 is open.\\nbrigade-end: done\\n", "done"),
            ("an indented declaration", "Pull request #96 is open.\\n  brigade-end: done", "done"),
            ("another last line", "Pull request #96 is open.", "undeclared"),
            ("another value", "Pull request #96 is open.\\nbrigade-end: finished", "undeclared"),
            ("a quotation above the last line", "The brief asks for brigade-end: done.\\nI stop here.", "undeclared"),
        ]
        for case, final_message, expected_outcome in rows:
            with self.subTest(case=case):
                # Arrange
                stdout = (
                    '{"type":"result","subtype":"success","is_error":false,"num_turns":12,'
                    f'"result":"{final_message}","session_id":"s-42"}}'
                )

                # Act
                result = parse_claude_output(stdout)

                # Assert
                self.assertEqual(result["outcome"], expected_outcome)

    def test_should_answer_failed_on_a_client_error_whatever_its_last_line_declares(self):
        # Arrange
        stdout = (
            '{"type":"result","subtype":"error_during_execution","is_error":true,"num_turns":12,'
            '"result":"brigade-end: done","session_id":"s-42"}'
        )

        # Act
        result = parse_claude_output(stdout, exit_code=1)

        # Assert
        self.assertEqual((result["outcome"], result["error_class"]), ("failed", "execution"))


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
                (
                    '{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","id":"t1",'
                    '"name":"Read","input":{"file_path":"/srv/b42/README.md","limit":40}}]}}\n'
                ),
                "Read /srv/b42/README.md",
            ),
            (
                "a command",
                (
                    '{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","id":"t1",'
                    '"name":"Bash","input":{"command":"python3 -m unittest","timeout":600}}]}}\n'
                ),
                "Bash python3 -m unittest",
            ),
            (
                "a pattern",
                (
                    '{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","id":"t1",'
                    '"name":"Grep","input":{"pattern":"def answer","path":"brigade"}}]}}\n'
                ),
                "Grep def answer",
            ),
            (
                "no argument",
                (
                    '{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","id":"t1",'
                    '"name":"TodoWrite","input":{"todos":[]}}]}}\n'
                ),
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
            (
                "done",
                '{"type":"result","subtype":"success","is_error":false,"num_turns":3,"result":"brigade-end: done"}\n',
                "done",
            ),
            ("undeclared", '{"type":"result","subtype":"success","is_error":false,"num_turns":3}\n', "undeclared"),
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
                    {
                        "role": "user",
                        "timestamp": "2026-10-06T10:00:00.000Z",
                        "content": "Deliver the task B42.",
                        "tool_calls": 0,
                        "id": None,
                        "usage": None,
                    },
                    {
                        "role": "assistant",
                        "timestamp": "2026-10-06T10:00:09.000Z",
                        "content": [{"type": "text", "text": "Done."}],
                        "tool_calls": 0,
                        "id": None,
                        "usage": None,
                    },
                ],
                "subagents": [],
            },
        )

    def test_should_count_the_tool_calls_of_each_message_and_read_each_sub_agent_of_the_session(self):
        # Arrange
        projects = Path(self.home.name) / ".claude" / "projects" / "-srv-b42"
        subagents = projects / "ada28962" / "subagents"
        subagents.mkdir(parents=True)
        (projects / "ada28962.jsonl").write_text(
            '{"type":"assistant","timestamp":"2026-10-06T10:00:09.000Z","message":{"role":"assistant",'
            '"content":[{"type":"text","text":"Reading."},{"type":"tool_use","name":"Read","input":{}},'
            '{"type":"tool_use","name":"Grep","input":{}}]}}\n'
        )
        (subagents / "agent-b2.jsonl").write_text(
            '{"type":"assistant","timestamp":"2026-10-06T10:01:00.000Z","message":{"role":"assistant",'
            '"content":[{"type":"tool_use","name":"Bash","input":{}}]}}\n'
        )
        (subagents / "agent-a1.jsonl").write_text(
            '{"type":"user","timestamp":"2026-10-06T10:00:30.000Z","message":{"role":"user","content":"Make it pass."}}\n'
        )
        (subagents / "agent-a1.meta.json").write_text('{"agentType":"ada"}')
        request = {
            "schema_version": 1,
            "session_id": "ada28962",
            "worktree": "/srv/b42",
            "reasoning_table": {},
            "settings": {},
            "home": self.home.name,
        }

        # Act
        transcripts = answer("transcripts", request)

        # Assert
        self.assertEqual(
            transcripts["messages"],
            [
                {
                    "role": "assistant",
                    "timestamp": "2026-10-06T10:00:09.000Z",
                    "content": [
                        {"type": "text", "text": "Reading."},
                        {"type": "tool_use", "name": "Read", "input": {}},
                        {"type": "tool_use", "name": "Grep", "input": {}},
                    ],
                    "tool_calls": 2,
                    "id": None,
                    "usage": None,
                },
            ],
        )
        self.assertCountEqual(
            transcripts["subagents"],
            [
                {
                    "messages": [
                        {
                            "role": "user",
                            "timestamp": "2026-10-06T10:00:30.000Z",
                            "content": "Make it pass.",
                            "tool_calls": 0,
                            "id": None,
                            "usage": None,
                        },
                    ]
                },
                {
                    "messages": [
                        {
                            "role": "assistant",
                            "timestamp": "2026-10-06T10:01:00.000Z",
                            "content": [{"type": "tool_use", "name": "Bash", "input": {}}],
                            "tool_calls": 1,
                            "id": None,
                            "usage": None,
                        },
                    ]
                },
            ],
        )

    def test_should_answer_the_id_and_the_four_usage_counters_of_each_message(self):
        # Arrange
        projects = Path(self.home.name) / ".claude" / "projects" / "-srv-b42"
        projects.mkdir(parents=True)
        (projects / "ada28962.jsonl").write_text(
            '{"type":"assistant","timestamp":"2026-10-06T10:00:09.000Z","message":{"role":"assistant",'
            '"id":"msg_01","content":[{"type":"text","text":"Done."}],"usage":{"input_tokens":3,"output_tokens":412,'
            '"cache_creation_input_tokens":2048,"cache_read_input_tokens":16384,"service_tier":"standard"}}}\n'
        )
        request = {
            "schema_version": 1,
            "session_id": "ada28962",
            "worktree": "/srv/b42",
            "reasoning_table": {},
            "settings": {},
            "home": self.home.name,
        }

        # Act
        transcripts = answer("transcripts", request)

        # Assert
        self.assertEqual(
            transcripts["messages"],
            [
                {
                    "role": "assistant",
                    "timestamp": "2026-10-06T10:00:09.000Z",
                    "content": [{"type": "text", "text": "Done."}],
                    "tool_calls": 0,
                    "id": "msg_01",
                    "usage": {
                        "input_tokens": 3,
                        "output_tokens": 412,
                        "cache_creation_input_tokens": 2048,
                        "cache_read_input_tokens": 16384,
                    },
                },
            ],
        )

    def test_should_ignore_the_last_line_a_killed_client_was_writing(self):
        # Arrange
        projects = Path(self.home.name) / ".claude" / "projects" / "-srv-b42"
        projects.mkdir(parents=True)
        (projects / "ada28962.jsonl").write_text(
            '{"type":"user","timestamp":"2026-10-06T10:00:00.000Z","message":{"role":"user","content":"Go."}}\n'
            '{"type":"assistant","timestamp":"2026-10-06T10:00:09.000Z","message":{"role":"assistant","content":[{"ty'
        )
        request = {
            "schema_version": 1,
            "session_id": "ada28962",
            "worktree": "/srv/b42",
            "reasoning_table": {},
            "settings": {},
            "home": self.home.name,
        }

        # Act
        transcripts = answer("transcripts", request)

        # Assert
        self.assertEqual(
            transcripts["messages"],
            [
                {
                    "role": "user",
                    "timestamp": "2026-10-06T10:00:00.000Z",
                    "content": "Go.",
                    "tool_calls": 0,
                    "id": None,
                    "usage": None,
                }
            ],
        )

    def test_should_refuse_a_session_file_whose_line_before_the_last_is_cut_short(self):
        # Arrange
        projects = Path(self.home.name) / ".claude" / "projects" / "-srv-b42"
        projects.mkdir(parents=True)
        (projects / "ada28962.jsonl").write_text(
            '{"type":"assistant","timestamp":"2026-10-06T10:00:09.000Z","message":{"role":"assi\n'
            '{"type":"user","timestamp":"2026-10-06T10:00:00.000Z","message":{"role":"user","content":"Go."}}\n'
            '{"type":"assistant","timestamp":"2026-10-06T10:00:10.000Z","message":{"role":"assistant","content":[{"ty'
        )
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
        self.assertIn(
            f"unreadable transcript at {self.home.name}/.claude/projects/-srv-b42/ada28962.jsonl: ",
            str(raised.exception),
        )

    def test_should_refuse_a_session_file_whose_usage_lacks_one_of_the_four_counters(self):
        # Arrange
        projects = Path(self.home.name) / ".claude" / "projects" / "-srv-b42"
        projects.mkdir(parents=True)
        (projects / "ada28962.jsonl").write_text(
            '{"type":"assistant","timestamp":"2026-10-06T10:00:10.000Z","message":{"id":"msg_b84","role":"assistant",'
            '"content":[],"usage":{"input_tokens":1,"output_tokens":10,"cache_creation_input_tokens":100}}}\n'
        )
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
            f"unreadable transcript at {self.home.name}/.claude/projects/-srv-b42/ada28962.jsonl:"
            " 'cache_read_input_tokens'",
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

    def test_should_refuse_a_session_file_it_cannot_parse(self):
        for case, transcript in [
            ("a line cut short", '{"type":"assistant","message":{"role":"assi\n'),
            ("a message entry without its message", '{"type":"assistant","timestamp":"2026-10-06T10:00:09.000Z"}\n'),
            ("a line that is not an object", '["assistant"]\n'),
            ("a message whose content is null", '{"type":"assistant","message":{"role":"assistant","content":null}}\n'),
        ]:
            with self.subTest(case=case):
                # Arrange
                projects = Path(self.home.name) / ".claude" / "projects" / "-srv-b42"
                projects.mkdir(parents=True, exist_ok=True)
                (projects / "ada28962.jsonl").write_text(transcript)
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
                self.assertIn(
                    f"unreadable transcript at {self.home.name}/.claude/projects/-srv-b42/ada28962.jsonl: ",
                    str(raised.exception),
                )

    def test_should_ignore_the_last_line_a_killed_sub_agent_was_writing(self):
        # Arrange
        projects = Path(self.home.name) / ".claude" / "projects" / "-srv-b42"
        subagents = projects / "ada28962" / "subagents"
        subagents.mkdir(parents=True)
        (projects / "ada28962.jsonl").write_text(
            '{"type":"user","timestamp":"2026-10-06T10:00:00.000Z","message":{"role":"user","content":"Go."}}\n'
        )
        (subagents / "agent-x.jsonl").write_text(
            '{"type":"user","timestamp":"2026-10-06T10:00:30.000Z","message":{"role":"user","content":"Make it pass."}}\n'
            '{"type":"assistant","timestamp":"2026-10-06T10:01:00.000Z","message":{"role":"assistant","content":[{"ty'
        )
        request = {
            "schema_version": 1,
            "session_id": "ada28962",
            "worktree": "/srv/b42",
            "reasoning_table": {},
            "settings": {},
            "home": self.home.name,
        }

        # Act
        transcripts = answer("transcripts", request)

        # Assert
        self.assertEqual(
            transcripts["subagents"],
            [
                {
                    "messages": [
                        {
                            "role": "user",
                            "timestamp": "2026-10-06T10:00:30.000Z",
                            "content": "Make it pass.",
                            "tool_calls": 0,
                            "id": None,
                            "usage": None,
                        }
                    ]
                }
            ],
        )

    def test_should_refuse_a_sub_agent_transcript_whose_line_before_the_last_is_cut_short(self):
        # Arrange
        projects = Path(self.home.name) / ".claude" / "projects" / "-srv-b42"
        subagents = projects / "ada28962" / "subagents"
        subagents.mkdir(parents=True)
        (projects / "ada28962.jsonl").write_text(
            '{"type":"user","timestamp":"2026-10-06T10:00:00.000Z","message":{"role":"user","content":"Go."}}\n'
        )
        (subagents / "agent-x.jsonl").write_text(
            '{"type":"assistant","timestamp":"2026-10-06T10:00:40.000Z","message":{"role":"assi\n'
            '{"type":"user","timestamp":"2026-10-06T10:00:30.000Z","message":{"role":"user","content":"Make it pass."}}\n'
            '{"type":"assistant","timestamp":"2026-10-06T10:01:00.000Z","message":{"role":"assistant","content":[{"ty'
        )
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
        self.assertIn(
            f"unreadable transcript at {self.home.name}/.claude/projects/-srv-b42/ada28962/subagents/agent-x.jsonl: ",
            str(raised.exception),
        )

    def test_should_refuse_a_sub_agent_transcript_it_cannot_open(self):
        # Arrange
        projects = Path(self.home.name) / ".claude" / "projects" / "-srv-b42"
        subagents = projects / "ada28962" / "subagents"
        (subagents / "agent-x.jsonl").mkdir(parents=True)
        (projects / "ada28962.jsonl").write_text(
            '{"type":"user","timestamp":"2026-10-06T10:00:00.000Z","message":{"role":"user","content":"Go."}}\n'
        )
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
        self.assertIn(
            f"unreadable transcript at {self.home.name}/.claude/projects/-srv-b42/ada28962/subagents/agent-x.jsonl: ",
            str(raised.exception),
        )
