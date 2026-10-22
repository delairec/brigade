import unittest
from pathlib import Path

from brigade.corpus.read_awawa_file_document import read_awawa_file_document
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

PLAN_FILE = "/srv/runs/r1/plan.awawa"


class ReadAwawaFileDocumentTest(unittest.TestCase):
    def test_should_answer_the_json_document_awawa_prints_on_the_file(self):
        # Arrange
        awawa = RecordingProcessRunner(
            {("awawa", "show", "@TASK.B20", "--json", PLAN_FILE): ProcessAnswer(stdout='{"fields": []}')}
        )

        # Act
        document = read_awawa_file_document(awawa, Path(PLAN_FILE), ("show", "@TASK.B20"))

        # Assert
        self.assertEqual(document, {"fields": []})

    def test_should_run_awawa_in_the_directory_of_the_file(self):
        # Arrange
        awawa = RecordingProcessRunner({("awawa", "show", PLAN_FILE, "--json", PLAN_FILE): ProcessAnswer(stdout="{}")})

        # Act
        read_awawa_file_document(awawa, Path(PLAN_FILE), ("show", PLAN_FILE))

        # Assert
        self.assertEqual(awawa.commands, [("/srv/runs/r1", ("awawa", "show", PLAN_FILE, "--json", PLAN_FILE))])
