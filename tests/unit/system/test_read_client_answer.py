import unittest

from brigade.errors import BrigadeError
from brigade.system.client_question import ClientQuestion
from brigade.system.client_role import ClientRole
from brigade.system.launch_argv_request import LaunchArgvRequest
from brigade.system.parse_result_request import ParseResultRequest
from brigade.system.probe_request import ProbeRequest
from brigade.system.read_client_answer import read_client_answer
from brigade.system.transcripts_request import TranscriptsRequest

PARSE_RESULT_QUESTION = ClientQuestion("vibe", ParseResultRequest(exit_code=0, stdout="", stderr=""))
LAUNCH_QUESTION = ClientQuestion(
    "vibe",
    LaunchArgvRequest(
        worktree="/work/b84",
        brief="Deliver the task B84.",
        role=ClientRole(
            name="ada",
            package="AGENT ada",
            package_file="/state/brigade/runs/r1/role.md",
            capabilities=("read", "write"),
            reasoning="standard",
            budget=75,
        ),
        progress_file="/state/brigade/runs/r1/progress.md",
        session_id="6f1c2a9e-3b7d-4e21-9a55-0c8d4b7e2f13",
        stop_at=None,
    ),
)
PROBE_QUESTION = ClientQuestion("vibe", ProbeRequest())
PROBE_WITH_ONE_ATTRIBUTION_LINE_AS_A_STRING = {
    "schema_version": 1,
    "client": "vibe",
    "version_argv": None,
    "operations": ["probe"],
    "features": [],
    "models": {},
    "attribution": "Co-Authored-By: Vibe <vibe@example.org>",
}
PROBE_WITH_AN_ATTRIBUTION_LINE_NOT_A_STRING = {
    "schema_version": 1,
    "client": "vibe",
    "version_argv": None,
    "operations": ["probe"],
    "features": [],
    "models": {},
    "attribution": ["Co-Authored-By: Vibe <vibe@example.org>", 1],
}
TRANSCRIPTS_QUESTION = ClientQuestion("vibe", TranscriptsRequest(session_id="session-b83", worktree="/work/b83"))
RESULT_WITHOUT_COST = {
    "schema_version": 1,
    "outcome": "done",
    "steps": 12,
    "usage": None,
    "session_id": "session-b83",
    "duration_ms": 60000,
    "error_class": None,
    "reset": None,
    "message": None,
}
LAUNCH_WITHOUT_SESSION = {"schema_version": 1, "argv": ["vibe"], "environment": {}, "stdin": "Deliver the task B84."}
TRANSCRIPTS_WITHOUT_TOOL_CALLS = {
    "schema_version": 1,
    "messages": [{"role": "assistant", "timestamp": None, "content": "Done."}],
    "subagents": [],
}
TRANSCRIPTS_WITHOUT_TOOLS = {
    "schema_version": 1,
    "messages": [
        {"role": "assistant", "timestamp": None, "content": "Done.", "tool_calls": 0, "id": None, "usage": None}
    ],
    "subagents": [],
}
TRANSCRIPTS_WITHOUT_MESSAGE_ID = {
    "schema_version": 1,
    "messages": [
        {"role": "assistant", "timestamp": None, "content": "Done.", "tool_calls": 0, "tools": [], "usage": None}
    ],
    "subagents": [],
}
TRANSCRIPTS_WITHOUT_MESSAGE_USAGE = {
    "schema_version": 1,
    "messages": [
        {"role": "assistant", "timestamp": None, "content": "Done.", "tool_calls": 0, "tools": [], "id": "msg_b84"}
    ],
    "subagents": [],
}


class ReadClientAnswerTest(unittest.TestCase):
    def test_should_refuse_an_answer_lacking_a_key_of_the_contract_naming_the_adapter_and_the_key(self):
        # Arrange
        cases = (
            (
                "a launch without its session",
                LAUNCH_QUESTION,
                LAUNCH_WITHOUT_SESSION,
                "client adapter vibe answered launch-argv: lacks the key session_id",
            ),
            (
                "a result without its cost",
                PARSE_RESULT_QUESTION,
                RESULT_WITHOUT_COST,
                "client adapter vibe answered parse-result: lacks the key cost_usd",
            ),
            (
                "a message without its tool calls",
                TRANSCRIPTS_QUESTION,
                TRANSCRIPTS_WITHOUT_TOOL_CALLS,
                "client adapter vibe answered transcripts: lacks the key messages[0].tool_calls",
            ),
            (
                "a message without its tools",
                TRANSCRIPTS_QUESTION,
                TRANSCRIPTS_WITHOUT_TOOLS,
                "client adapter vibe answered transcripts: lacks the key messages[0].tools",
            ),
            (
                "a message without its id",
                TRANSCRIPTS_QUESTION,
                TRANSCRIPTS_WITHOUT_MESSAGE_ID,
                "client adapter vibe answered transcripts: lacks the key messages[0].id",
            ),
            (
                "a message without its usage",
                TRANSCRIPTS_QUESTION,
                TRANSCRIPTS_WITHOUT_MESSAGE_USAGE,
                "client adapter vibe answered transcripts: lacks the key messages[0].usage",
            ),
        )
        for name, question, answer, expected_message in cases:
            with self.subTest(name):
                # Act
                with self.assertRaises(BrigadeError) as raised:
                    read_client_answer(question, answer)

                # Assert
                self.assertEqual(str(raised.exception), expected_message)

    def test_should_read_the_edit_tools_a_probe_names(self):
        # Arrange
        probe = {
            "schema_version": 1,
            "client": "vibe",
            "version_argv": None,
            "operations": ["probe"],
            "features": [],
            "models": {},
            "edit_tools": ["write_file"],
        }

        # Act
        answer = read_client_answer(PROBE_QUESTION, probe)

        # Assert
        self.assertEqual(answer.edit_tools, ("write_file",))

    def test_should_read_no_edit_tool_from_a_probe_that_names_none(self):
        # Arrange
        probe = {
            "schema_version": 1,
            "client": "vibe",
            "version_argv": None,
            "operations": [],
            "features": [],
            "models": {},
        }

        # Act
        answer = read_client_answer(PROBE_QUESTION, probe)

        # Assert
        self.assertEqual(answer.edit_tools, ())

    def test_should_refuse_a_probe_whose_attribution_is_not_a_list_of_lines(self):
        # Arrange
        cases = (
            (
                "one line written as a string",
                PROBE_WITH_ONE_ATTRIBUTION_LINE_AS_A_STRING,
                "client adapter vibe answered probe: attribution is a string, not a list",
            ),
            (
                "a line that is not a string",
                PROBE_WITH_AN_ATTRIBUTION_LINE_NOT_A_STRING,
                "client adapter vibe answered probe: attribution[1] is an integer, not a string",
            ),
        )
        for name, answer, expected_message in cases:
            with self.subTest(name):
                # Act
                with self.assertRaises(BrigadeError) as raised:
                    read_client_answer(PROBE_QUESTION, answer)

                # Assert
                self.assertEqual(str(raised.exception), expected_message)
