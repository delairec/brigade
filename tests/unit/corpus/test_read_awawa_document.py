import unittest
from pathlib import Path

from brigade.corpus.read_awawa_document import read_awawa_document
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


class ReadAwawaDocumentTest(unittest.TestCase):
    def test_should_answer_the_json_document_awawa_prints(self):
        # Arrange
        awawa = RecordingProcessRunner(
            {("awawa", "status", "TASK", "--json", "/srv/shop"): ProcessAnswer(stdout='{"entities": []}')}
        )

        # Act
        document = read_awawa_document(awawa, Path("/srv/shop"), ("status", "TASK"))

        # Assert
        self.assertEqual(document, {"entities": []})
