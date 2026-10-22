import unittest
from pathlib import Path

from brigade.corpus.check_type_declared import check_type_declared
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

UNDECLARED_TYPE = 1
MISSING_ROOT = 2


class CheckTypeDeclaredTest(unittest.TestCase):
    def test_should_answer_that_the_schema_declares_the_type(self):
        # Arrange
        awawa = RecordingProcessRunner(
            {("awawa", "show", "FINDING", "/srv/corpus"): ProcessAnswer(stdout="SCHEMA FINDING\n")}
        )

        # Act
        declared = check_type_declared(awawa, Path("/srv/corpus"), "FINDING")

        # Assert
        self.assertTrue(declared)

    def test_should_answer_that_the_schema_does_not_declare_the_type_whatever_awawa_refuses(self):
        for exit_code in (UNDECLARED_TYPE, MISSING_ROOT):
            with self.subTest(exit_code=exit_code):
                # Arrange
                awawa = RecordingProcessRunner(
                    {("awawa", "show", "VERDICT", "/srv/corpus"): ProcessAnswer(exit_code=exit_code)}
                )

                # Act
                declared = check_type_declared(awawa, Path("/srv/corpus"), "VERDICT")

                # Assert
                self.assertFalse(declared)
