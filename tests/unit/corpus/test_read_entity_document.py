import json
import unittest
from pathlib import Path

from brigade.corpus.read_entity_document import read_entity_document
from brigade.errors import CommandFailed
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

ROOT = Path("/srv/shop-head")
SHOW_B1 = ("awawa", "show", "@TASK.B1", "--json", "/srv/shop-head")


class ReadEntityDocumentTest(unittest.TestCase):
    def test_should_give_the_document_awawa_shows_for_a_defined_entity(self):
        # Arrange
        shown = {"name": "B1", "fields": [{"name": "STATUS", "atoms": ["implemented"], "fields": []}]}
        awawa = RecordingProcessRunner({SHOW_B1: ProcessAnswer(stdout=json.dumps(shown))})

        # Act
        document = read_entity_document(awawa, ROOT, "@TASK.B1")

        # Assert
        self.assertEqual(
            document, {"name": "B1", "fields": [{"name": "STATUS", "atoms": ["implemented"], "fields": []}]}
        )

    def test_should_give_nothing_for_an_entity_awawa_says_is_not_defined(self):
        # Arrange
        not_defined = ProcessAnswer(exit_code=1, stderr="awawa show: @TASK.B1 is not defined in the workspace\n")
        awawa = RecordingProcessRunner({SHOW_B1: not_defined})

        # Act
        document = read_entity_document(awawa, ROOT, "@TASK.B1")

        # Assert
        self.assertIsNone(document)

    def test_should_fail_on_any_other_failure_of_awawa(self):
        cases = [
            (
                ProcessAnswer(exit_code=1, stderr="awawa show: the schema declares no TASK\n"),
                "awawa show @TASK.B1 --json /srv/shop-head exited 1: awawa show: the schema declares no TASK",
            ),
            (
                ProcessAnswer(exit_code=2, stderr="awawa: corpus/tasks.awawa is not UTF-8\n"),
                "awawa show @TASK.B1 --json /srv/shop-head exited 2: awawa: corpus/tasks.awawa is not UTF-8",
            ),
        ]
        for failure, message in cases:
            with self.subTest(message=message):
                # Arrange
                awawa = RecordingProcessRunner({SHOW_B1: failure})

                # Act
                with self.assertRaises(CommandFailed) as raised:
                    read_entity_document(awawa, ROOT, "@TASK.B1")

                # Assert
                self.assertEqual(str(raised.exception), message)
