import unittest

from brigade.errors import BrigadeError
from brigade.system.client_question import ClientQuestion
from brigade.system.parse_result_request import ParseResultRequest
from brigade.system.read_client_answer import read_client_answer
from brigade.system.transcripts_request import TranscriptsRequest

PARSE_RESULT_QUESTION = ClientQuestion("vibe", ParseResultRequest(exit_code=0, stdout="", stderr=""))
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
TRANSCRIPTS_WITHOUT_TOOL_CALLS = {
    "schema_version": 1,
    "messages": [{"role": "assistant", "timestamp": None, "content": "Done."}],
    "subagents": [],
}


class ReadClientAnswerTest(unittest.TestCase):
    def test_should_refuse_an_answer_lacking_a_key_of_the_contract_naming_the_adapter_and_the_key(self):
        cases = (
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
        )
        for name, question, answer, expected_message in cases:
            with self.subTest(name):
                # Act
                with self.assertRaises(BrigadeError) as raised:
                    read_client_answer(question, answer)

                # Assert
                self.assertEqual(str(raised.exception), expected_message)
