import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.adapters.clients.claude_code import answer
from brigade.runs.count_session_steps import SessionSteps, count_session_steps
from brigade.system.transcripts_answer import TranscriptsAnswer

FIXTURES = Path(__file__).parents[1] / "adapters" / "clients" / "fixtures" / "claude-code"
SESSION_857D4221 = "857d4221-e962-4128-8096-759d8feb0ced"


class CountSessionStepsTest(unittest.TestCase):
    def test_should_count_the_tool_calls_of_the_main_transcript_plus_one(self):
        # Arrange
        transcripts = TranscriptsAnswer.from_document(
            {
                "schema_version": 1,
                "messages": [
                    {"role": "user", "timestamp": None, "content": "Deliver the task.", "tool_calls": 0},
                    {"role": "assistant", "timestamp": None, "content": [], "tool_calls": 2},
                    {"role": "assistant", "timestamp": None, "content": [], "tool_calls": 3},
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
                "messages": [{"role": "assistant", "timestamp": None, "content": [], "tool_calls": 1}],
                "subagents": [
                    {"messages": [{"role": "assistant", "timestamp": None, "content": [], "tool_calls": 4}]},
                    {"messages": [{"role": "user", "timestamp": None, "content": "Read it.", "tool_calls": 0}]},
                ],
            }
        )

        # Act
        steps = count_session_steps(transcripts)

        # Assert
        self.assertEqual(steps, SessionSteps(main_steps=2, total_steps=8))


class CountSessionStepsOfSession857d4221Test(unittest.TestCase):
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

    def test_should_count_the_main_session_and_its_one_sub_agent(self):
        # Arrange
        transcripts = TranscriptsAnswer.from_document(
            answer(
                "transcripts",
                {
                    "schema_version": 1,
                    "session_id": SESSION_857D4221,
                    "worktree": "/srv/worktrees/b71",
                    "reasoning_table": {},
                    "settings": {},
                    "home": str(self.home),
                },
            )
        )

        # Act
        steps = count_session_steps(transcripts)

        # Assert
        self.assertEqual(steps, SessionSteps(main_steps=42, total_steps=54))
