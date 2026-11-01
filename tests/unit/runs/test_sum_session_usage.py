import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.adapters.clients.claude_code import answer
from brigade.runs.sum_session_usage import sum_session_usage
from brigade.system.token_usage import TokenUsage
from brigade.system.transcripts_answer import TranscriptsAnswer

FIXTURES = Path(__file__).parents[1] / "adapters" / "clients" / "fixtures" / "claude-code"
SESSION_A47607D0 = "a47607d0-5a3d-4910-8978-9aad5d0e7796"
SESSION_DE26D2C6 = "de26d2c6-3b58-4d9e-9bb4-292f6b9e64de"
NO_USAGE = None
NO_ID = None


class SumSessionUsageTest(unittest.TestCase):
    def test_should_count_each_message_of_the_session_and_of_its_sub_agents_once(self):
        # Arrange
        transcripts = TranscriptsAnswer.from_document(
            {
                "schema_version": 1,
                "messages": [
                    {
                        "role": "user",
                        "timestamp": None,
                        "content": "Go.",
                        "tool_calls": 0,
                        "tools": [],
                        "id": NO_ID,
                        "usage": NO_USAGE,
                    },
                    {
                        "role": "assistant",
                        "timestamp": None,
                        "content": [{"type": "text"}],
                        "tool_calls": 0,
                        "tools": [],
                        "id": "msg_01",
                        "usage": {
                            "input_tokens": 1,
                            "output_tokens": 10,
                            "cache_creation_input_tokens": 100,
                            "cache_read_input_tokens": 1000,
                        },
                    },
                    {
                        "role": "assistant",
                        "timestamp": None,
                        "content": [{"type": "tool_use"}],
                        "tool_calls": 1,
                        "tools": [],
                        "id": "msg_01",
                        "usage": {
                            "input_tokens": 1,
                            "output_tokens": 10,
                            "cache_creation_input_tokens": 100,
                            "cache_read_input_tokens": 1000,
                        },
                    },
                ],
                "subagents": [
                    {
                        "messages": [
                            {
                                "role": "assistant",
                                "timestamp": None,
                                "content": [{"type": "tool_use"}],
                                "tool_calls": 1,
                                "tools": [],
                                "id": "msg_02",
                                "usage": {
                                    "input_tokens": 2,
                                    "output_tokens": 20,
                                    "cache_creation_input_tokens": 200,
                                    "cache_read_input_tokens": 2000,
                                },
                            },
                        ]
                    },
                ],
            }
        )

        # Act
        usage = sum_session_usage(transcripts)

        # Assert
        self.assertEqual(
            usage,
            TokenUsage(input_tokens=3, output_tokens=30, cache_creation_input_tokens=300, cache_read_input_tokens=3000),
        )

    def test_should_count_each_message_without_an_id_on_its_own(self):
        # Arrange
        transcripts = TranscriptsAnswer.from_document(
            {
                "schema_version": 1,
                "messages": [
                    {
                        "role": "assistant",
                        "timestamp": None,
                        "content": "Reading the task.",
                        "tool_calls": 0,
                        "tools": [],
                        "id": NO_ID,
                        "usage": {
                            "input_tokens": 1,
                            "output_tokens": 10,
                            "cache_creation_input_tokens": 100,
                            "cache_read_input_tokens": 1000,
                        },
                    },
                    {
                        "role": "assistant",
                        "timestamp": None,
                        "content": "Writing the test.",
                        "tool_calls": 0,
                        "tools": [],
                        "id": NO_ID,
                        "usage": {
                            "input_tokens": 1,
                            "output_tokens": 10,
                            "cache_creation_input_tokens": 100,
                            "cache_read_input_tokens": 1000,
                        },
                    },
                ],
                "subagents": [
                    {
                        "messages": [
                            {
                                "role": "assistant",
                                "timestamp": None,
                                "content": "Done.",
                                "tool_calls": 0,
                                "tools": [],
                                "id": NO_ID,
                                "usage": {
                                    "input_tokens": 1,
                                    "output_tokens": 10,
                                    "cache_creation_input_tokens": 100,
                                    "cache_read_input_tokens": 1000,
                                },
                            },
                        ]
                    },
                ],
            }
        )

        # Act
        usage = sum_session_usage(transcripts)

        # Assert
        self.assertEqual(
            usage,
            TokenUsage(input_tokens=3, output_tokens=30, cache_creation_input_tokens=300, cache_read_input_tokens=3000),
        )


class SumSessionUsageOfRecordedSessionsTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.home = Path(directory.name)
        project = self.home / ".claude" / "projects" / "-srv-worktrees-b82"
        project.mkdir(parents=True)
        shutil.copyfile(FIXTURES / "session-a47607d0.jsonl", project / f"{SESSION_A47607D0}.jsonl")
        shutil.copyfile(FIXTURES / "session-de26d2c6.jsonl", project / f"{SESSION_DE26D2C6}.jsonl")

    def read_transcripts(self, session_id: str) -> TranscriptsAnswer:
        return TranscriptsAnswer.from_document(
            answer(
                "transcripts",
                {
                    "schema_version": 1,
                    "session_id": session_id,
                    "worktree": "/srv/worktrees/b82",
                    "reasoning_table": {},
                    "settings": {},
                    "home": str(self.home),
                },
            )
        )

    def test_should_sum_the_usage_of_a_recorded_session_over_its_distinct_messages(self):
        # Arrange
        rows = [
            (
                "a session cut at the wall-time limit",
                SESSION_A47607D0,
                TokenUsage(
                    input_tokens=188,
                    output_tokens=88524,
                    cache_creation_input_tokens=240807,
                    cache_read_input_tokens=16937660,
                ),
            ),
            (
                "a session whose result object reports this usage",
                SESSION_DE26D2C6,
                TokenUsage(
                    input_tokens=64,
                    output_tokens=26366,
                    cache_creation_input_tokens=91281,
                    cache_read_input_tokens=3163768,
                ),
            ),
        ]
        for case, session_id, expected_usage in rows:
            with self.subTest(case):
                # Arrange
                transcripts = self.read_transcripts(session_id)

                # Act
                usage = sum_session_usage(transcripts)

                # Assert
                self.assertEqual(usage, expected_usage)
