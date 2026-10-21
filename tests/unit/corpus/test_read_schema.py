import unittest
from pathlib import Path

from brigade.corpus.read_schema import read_schema
from brigade.errors import CommandFailed
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

UNDECLARED_TYPE = 1
MISSING_ROOT = 2


class ReadSchemaTest(unittest.TestCase):
    def test_should_answer_the_schema_of_a_declared_type_as_awawa_prints_it(self):
        # Arrange
        awawa = RecordingProcessRunner(
            {("awawa", "show", "TASK", "/srv/shop"): ProcessAnswer(stdout='SCHEMA TASK\n\tDESC "a change"\n')}
        )

        # Act
        schema = read_schema(awawa, Path("/srv/shop"), "TASK")

        # Assert
        self.assertEqual(schema, 'SCHEMA TASK\n\tDESC "a change"\n')

    def test_should_answer_no_schema_for_a_type_the_corpus_does_not_declare(self):
        # Arrange
        awawa = RecordingProcessRunner(
            {("awawa", "show", "MILESTONE", "/srv/shop"): ProcessAnswer(exit_code=UNDECLARED_TYPE)}
        )

        # Act
        schema = read_schema(awawa, Path("/srv/shop"), "MILESTONE")

        # Assert
        self.assertIsNone(schema)

    def test_should_fail_on_any_other_refusal_of_awawa(self):
        # Arrange
        awawa = RecordingProcessRunner(
            {("awawa", "show", "TASK", "/srv/gone"): ProcessAnswer(exit_code=MISSING_ROOT, stderr="no workspace")}
        )

        # Act
        with self.assertRaises(CommandFailed) as failure:
            read_schema(awawa, Path("/srv/gone"), "TASK")

        # Assert
        self.assertEqual(str(failure.exception), "awawa show TASK /srv/gone exited 2: no workspace")
