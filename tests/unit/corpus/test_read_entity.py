import unittest
from pathlib import Path

from brigade.corpus.read_entity import read_entity
from brigade.errors import EntityNotDefined, ToolFailure
from brigade.system.run_process import ProcessRecord, ProcessRequest

INSTRUCTIONS = Path("/srv/instructions")


def create_awawa_exiting(exit_code: int, stderr: str):
    def answer(request: ProcessRequest) -> ProcessRecord:
        return ProcessRecord(
            argv=request.argv, cwd=request.cwd, exit_code=exit_code, stdout="", stderr=stderr, duration_ms=1
        )

    return answer


class ReadEntityOfAnEntityAwawaDoesNotKnowTest(unittest.TestCase):
    def test_should_refuse_naming_the_entity_and_the_corpus(self):
        # Arrange
        awawa = create_awawa_exiting(1, "awawa show: @AGENT.planner is not defined in the workspace\n")

        # Act
        with self.assertRaises(EntityNotDefined) as refusal:
            read_entity(awawa, INSTRUCTIONS, "AGENT", "planner")

        # Assert
        self.assertEqual(str(refusal.exception), "@AGENT.planner is not defined in /srv/instructions")


class ReadEntityOfAnExit1AwawaDoesNotExplainByAnUnknownEntityTest(unittest.TestCase):
    def test_should_refuse_naming_the_command_and_its_stderr(self):
        # Arrange
        awawa = create_awawa_exiting(1, "awawa: the workspace holds two schemas\n")

        # Act
        with self.assertRaises(ToolFailure) as refusal:
            read_entity(awawa, INSTRUCTIONS, "AGENT", "planner")

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "awawa show @AGENT.planner --json /srv/instructions exited 1: awawa: the workspace holds two schemas",
        )


class ReadEntityOfAnAwawaTimedOutTest(unittest.TestCase):
    def test_should_let_the_failure_of_the_command_through(self):
        # Arrange
        def time_out(request: ProcessRequest) -> ProcessRecord:
            raise ToolFailure("awawa show @AGENT.planner --json /srv/instructions timed out after 30 s")

        # Act
        with self.assertRaises(ToolFailure) as refusal:
            read_entity(time_out, INSTRUCTIONS, "AGENT", "planner")

        # Assert
        self.assertEqual(
            str(refusal.exception), "awawa show @AGENT.planner --json /srv/instructions timed out after 30 s"
        )
