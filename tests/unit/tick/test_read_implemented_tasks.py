import json
import unittest
from pathlib import Path

from brigade.tick.read_implemented_tasks import read_implemented_tasks
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


class ReadImplementedTasksTest(unittest.TestCase):
    def test_should_answer_the_tasks_the_corpus_marks_implemented(self):
        # Arrange
        awawa = RecordingProcessRunner(
            {
                ("awawa", "status", "TASK", "--where", "STATUS==implemented", "--json", "/srv/shop"): ProcessAnswer(
                    stdout=json.dumps({"entities": [{"type": "TASK", "name": "B1"}, {"type": "TASK", "name": "B2"}]})
                )
            }
        )

        # Act
        implemented = read_implemented_tasks(awawa, Path("/srv/shop"))

        # Assert
        self.assertEqual(implemented, ("B1", "B2"))
