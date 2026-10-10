import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.adapters.clients.claude_code import answer
from brigade.runs.count_session_steps import SessionSteps, count_session_steps
from brigade.system.transcripts_answer import TranscriptsAnswer

FIXTURES = Path(__file__).parents[1] / "adapters" / "clients" / "fixtures" / "claude-code"
SESSION_857D4221 = "857d4221-e962-4128-8096-759d8feb0ced"
SESSION_DE26D2C6 = "de26d2c6-3b58-4d9e-9bb4-292f6b9e64de"
SESSION_A47607D0 = "a47607d0-5a3d-4910-8978-9aad5d0e7796"


class CountSessionStepsTest(unittest.TestCase):
    def test_should_count_the_tool_calls_of_the_main_transcript_plus_one(self):
        # Arrange
        transcripts = TranscriptsAnswer.from_document(
            {
                "schema_version": 1,
                "messages": [
                    {
                        "role": "user",
                        "timestamp": None,
                        "content": "Deliver the task.",
                        "tool_calls": 0,
                        "id": None,
                        "usage": None,
                    },
                    {"role": "assistant", "timestamp": None, "content": [], "tool_calls": 2, "id": None, "usage": None},
                    {"role": "assistant", "timestamp": None, "content": [], "tool_calls": 3, "id": None, "usage": None},
                ],
                "subagents": [],
            }
        )

        # Act
        steps = count_session_steps(transcripts)

        # Assert
        self.assertEqual(steps, SessionSteps(main_steps=6, total_steps=6))

    def test_should_add_the_steps_of_each_sub_agent_counted_the_same_way(self):
        # Arrange
        transcripts = TranscriptsAnswer.from_document(
            {
                "schema_version": 1,
                "messages": [
                    {"role": "assistant", "timestamp": None, "content": [], "tool_calls": 1, "id": None, "usage": None}
                ],
                "subagents": [
                    {
                        "messages": [
                            {
                                "role": "assistant",
                                "timestamp": None,
                                "content": [],
                                "tool_calls": 4,
                                "id": None,
                                "usage": None,
                            }
                        ]
                    },
                    {
                        "messages": [
                            {
                                "role": "user",
                                "timestamp": None,
                                "content": "Read it.",
                                "tool_calls": 0,
                                "id": None,
                                "usage": None,
                            }
                        ]
                    },
                ],
            }
        )

        # Act
        steps = count_session_steps(transcripts)

        # Assert
        self.assertEqual(steps, SessionSteps(main_steps=2, total_steps=8))


class CountSessionStepsOfRecordedSessionsTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.home = Path(directory.name)
        project = self.home / ".claude" / "projects" / "-srv-worktrees-b71"
        subagents = project / SESSION_857D4221 / "subagents"
        subagents.mkdir(parents=True)
        shutil.copyfile(FIXTURES / "session-857d4221.jsonl", project / f"{SESSION_857D4221}.jsonl")
        shutil.copyfile(
            FIXTURES / "session-857d4221-agent-a9ba9e367d37d17b5.jsonl", subagents / "agent-a9ba9e367d37d17b5.jsonl"
        )
        shutil.copyfile(FIXTURES / "session-de26d2c6.jsonl", project / f"{SESSION_DE26D2C6}.jsonl")
        shutil.copyfile(FIXTURES / "session-a47607d0.jsonl", project / f"{SESSION_A47607D0}.jsonl")

    def read_transcripts(self, session_id: str) -> TranscriptsAnswer:
        return TranscriptsAnswer.from_document(
            answer(
                "transcripts",
                {
                    "schema_version": 1,
                    "session_id": session_id,
                    "worktree": "/srv/worktrees/b71",
                    "reasoning_table": {},
                    "settings": {},
                    "home": str(self.home),
                },
            )
        )

    def test_should_count_the_main_session_and_its_one_sub_agent(self):
        # Arrange
        transcripts = self.read_transcripts(SESSION_857D4221)

        # Act
        steps = count_session_steps(transcripts)

        # Assert
        self.assertEqual(steps, SessionSteps(main_steps=42, total_steps=54))

    def test_should_count_as_many_main_steps_as_the_turns_the_client_reported_for_a_session_ending_on_no_notification(
        self,
    ):
        # Arrange
        transcripts = self.read_transcripts(SESSION_DE26D2C6)

        # Act
        steps = count_session_steps(transcripts)

        # Assert
        self.assertEqual(steps, SessionSteps(main_steps=52, total_steps=52))

    def test_should_count_the_steps_of_a_session_cut_at_the_wall_time_limit(self):
        # Arrange
        transcripts = self.read_transcripts(SESSION_A47607D0)

        # Act
        steps = count_session_steps(transcripts)

        # Assert
        self.assertEqual(steps, SessionSteps(main_steps=106, total_steps=106))
