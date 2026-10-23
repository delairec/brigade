import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.study_resume import COMMAND
from tests.unit.commands.command_runtime import create_corpus_double, write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

ACTIVE_STUDY = (("SLOT", "report"), ("OUTPUT", "file:/home/user/health.md"), ("ANSWER", "ANSWER"), ("STATUS", "active"))


class StudyResumeTextTest(unittest.TestCase):
    def test_should_say_whether_the_study_was_resumed(self):
        # Arrange
        rows = [
            ("a study resumed", True, "resumed @STUDY.health"),
            ("a study already active", False, "@STUDY.health is already active"),
        ]
        for case, changed, expected_text in rows:
            with self.subTest(case=case):
                # Act
                text = COMMAND.render_text(
                    {"schema_version": 1, "study": "health", "status": "active", "changed": changed}
                )

                # Assert
                self.assertEqual(text, expected_text)


class StudyResumeExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1})

        # Assert
        self.assertEqual(exit_code, 0)


class StudyResumeRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(name="health")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class StudyResumeOfAnActiveStudyTest(unittest.TestCase):
    def test_should_leave_an_active_study_unchanged(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        runtime = create_test_runtime(
            create_test_paths(root), run_process=create_corpus_double({"STUDY": {"health": ACTIVE_STUDY}})
        )

        # Act
        document = COMMAND.run(Namespace(name="health"), runtime)

        # Assert
        self.assertEqual(document, {"schema_version": 1, "study": "health", "status": "active", "changed": False})
