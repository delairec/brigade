import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.study_pause import COMMAND
from tests.unit.commands.command_runtime import create_corpus_double, create_runtime, write_operational_corpus

PAUSED_STUDY = (("SLOT", "report"), ("OUTPUT", "file:/home/user/health.md"), ("ANSWER", "ANSWER"), ("STATUS", "paused"))


class StudyPauseTextTest(unittest.TestCase):
    def test_should_say_whether_the_study_was_paused(self):
        # Arrange
        rows = [
            ("a study paused", True, "paused @STUDY.health"),
            ("a study already paused", False, "@STUDY.health is already paused"),
        ]
        for case, changed, expected_text in rows:
            with self.subTest(case=case):
                # Act
                text = COMMAND.render_text(
                    {"schema_version": 1, "study": "health", "status": "paused", "changed": changed}
                )

                # Assert
                self.assertEqual(text, expected_text)


class StudyPauseExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1})

        # Assert
        self.assertEqual(exit_code, 0)


class StudyPauseRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(name="health")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class StudyPauseOfAPausedStudyTest(unittest.TestCase):
    def test_should_leave_a_paused_study_unchanged(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        runtime = create_runtime(root, run_process=create_corpus_double({"STUDY": {"health": PAUSED_STUDY}}))

        # Act
        document = COMMAND.run(Namespace(name="health"), runtime)

        # Assert
        self.assertEqual(document, {"schema_version": 1, "study": "health", "status": "paused", "changed": False})
