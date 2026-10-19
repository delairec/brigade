import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from brigade.commands.study_context import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import create_runtime

RUN_ID = "20261019T090000Z-e10d04"


class StudyContextTextTest(unittest.TestCase):
    def test_should_print_the_question_the_collected_documents_the_answer_and_the_schema(self):
        # Arrange
        document = {
            "question": "is the machine healthy?",
            "collected": [{"collector": "runs-list", "summary": {"runs": 2}, "document": "/runs/1/runs-list.json"}],
            "prose_fields": ["VERDICT", "REASON"],
            "answer": "ANSWER health_1\n",
            "schema": "SCHEMA ANSWER\n",
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "question: is the machine healthy?\n"
            'runs-list: {"runs": 2}, /runs/1/runs-list.json\n'
            "prose fields left to the slot: VERDICT, REASON\n"
            "\n"
            "ANSWER health_1\n"
            "\n"
            "SCHEMA ANSWER",
        )


class StudyContextExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({})

        # Assert
        self.assertEqual(exit_code, 0)


class StudyContextRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = SimpleNamespace(run=RUN_ID)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class StudyContextOfARunTest(unittest.TestCase):
    def test_should_refuse_a_run_that_is_not_a_run_of_a_study(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (root / "state" / "runs" / RUN_ID).mkdir(parents=True)

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(SimpleNamespace(run=RUN_ID), create_runtime(root))

        # Assert
        self.assertEqual(str(raised.exception), f"{RUN_ID} is not a run of a study")
