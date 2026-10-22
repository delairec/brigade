import unittest
from pathlib import Path

from brigade.corpus.read_entity_template import read_entity_template
from brigade.errors import CommandFailed
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

UNDECLARED_TYPE = 1
MISSING_ROOT = 2


class ReadEntityTemplateTest(unittest.TestCase):
    def test_should_answer_the_template_awawa_prints_for_a_new_entity(self):
        # Arrange
        awawa = RecordingProcessRunner(
            {("awawa", "new", "TASK", "B12", "/srv/oak"): ProcessAnswer(stdout='TASK B12\n\tTITLE ""\n')}
        )

        # Act
        template = read_entity_template(awawa, Path("/srv/oak"), "TASK", "B12")

        # Assert
        self.assertEqual(template, 'TASK B12\n\tTITLE ""\n')

    def test_should_answer_no_template_for_a_type_the_corpus_does_not_declare(self):
        # Arrange
        awawa = RecordingProcessRunner(
            {("awawa", "new", "EPIC", "E1", "/srv/oak"): ProcessAnswer(exit_code=UNDECLARED_TYPE)}
        )

        # Act
        template = read_entity_template(awawa, Path("/srv/oak"), "EPIC", "E1")

        # Assert
        self.assertIsNone(template)

    def test_should_fail_on_any_other_refusal_of_awawa(self):
        # Arrange
        awawa = RecordingProcessRunner(
            {("awawa", "new", "TASK", "B12", "/srv/gone"): ProcessAnswer(exit_code=MISSING_ROOT, stderr="no workspace")}
        )

        # Act
        with self.assertRaises(CommandFailed) as failure:
            read_entity_template(awawa, Path("/srv/gone"), "TASK", "B12")

        # Assert
        self.assertEqual(str(failure.exception), "awawa new TASK B12 /srv/gone exited 2: no workspace")
