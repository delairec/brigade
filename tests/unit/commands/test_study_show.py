import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.study_show import COMMAND
from tests.unit.commands.command_runtime import create_corpus_double, write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime


class StudyShowTextTest(unittest.TestCase):
    def test_should_print_each_field_then_the_last_run(self):
        # Arrange
        rows = [
            ("a study never run", None, None, "last run    -\noutcome     -"),
            ("a study run", "20261018T090000Z-a1", "done", "last run    20261018T090000Z-a1\noutcome     done"),
        ]
        for case, last_run, outcome, expected_ending in rows:
            with self.subTest(case=case):
                # Arrange
                document = {
                    "schema_version": 1,
                    "study": {
                        "name": "health",
                        "fields": [{"name": "TITLE", "value": "the health of the machine"}],
                        "last_run": last_run,
                        "outcome": outcome,
                    },
                }

                # Act
                text = COMMAND.render_text(document)

                # Assert
                self.assertEqual(text, f"@STUDY.health\nTITLE       the health of the machine\n{expected_ending}")


class StudyShowExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1})

        # Assert
        self.assertEqual(exit_code, 0)


class StudyShowRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(name="health")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class StudyShowOfARecordedStudyTest(unittest.TestCase):
    def test_should_show_the_fields_of_a_study_never_run(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        entities = {"STUDY": {"health": (("TITLE", "the health of the machine"), ("STATUS", "active"))}}
        runtime = create_test_runtime(create_test_paths(root), run_process=create_corpus_double(entities))

        # Act
        document = COMMAND.run(Namespace(name="health"), runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "study": {
                    "name": "health",
                    "fields": [
                        {"name": "TITLE", "value": "the health of the machine"},
                        {"name": "STATUS", "value": "active"},
                    ],
                    "last_run": None,
                    "outcome": None,
                },
            },
        )
