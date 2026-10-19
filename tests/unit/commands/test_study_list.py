import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from brigade.commands.study_list import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import create_corpus_double, create_runtime, write_operational_corpus

HEALTH_STUDY = (
    ("TITLE", "the health of the machine"),
    ("COLLECTOR", "runs-list"),
    ("SLOT", "report"),
    ("EVERY", "1d"),
    ("OUTPUT", "file:/home/user/health.md"),
    ("ANSWER", "ANSWER"),
    ("STATUS", "active"),
)


class StudyListTextTest(unittest.TestCase):
    def test_should_say_that_no_study_is_recorded(self):
        # Act
        text = COMMAND.render_text({"schema_version": 1, "studies": []})

        # Assert
        self.assertEqual(text, "no study recorded")

    def test_should_print_one_row_per_study_marking_what_is_absent(self):
        # Arrange
        document = {
            "schema_version": 1,
            "studies": [
                {"name": "health", "status": "active", "every": None, "last_run": None, "outcome": None},
                {
                    "name": "debt",
                    "status": "paused",
                    "every": "1w",
                    "last_run": "20261018T090000Z-a1",
                    "outcome": "done",
                },
            ],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "name    status  every  last run             outcome\n"
            "health  active  -      -                    -\n"
            "debt    paused  1w     20261018T090000Z-a1  done",
        )


class StudyListExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1, "studies": []})

        # Assert
        self.assertEqual(exit_code, 0)


class StudyListRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = SimpleNamespace(json=False)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class StudyListOfTheOperationalCorpusTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_should_list_each_study_with_its_schedule(self):
        # Arrange
        write_operational_corpus(self.root)
        runtime = create_runtime(self.root, run_process=create_corpus_double({"STUDY": {"health": HEALTH_STUDY}}))

        # Act
        document = COMMAND.run(SimpleNamespace(), runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "studies": [{"name": "health", "status": "active", "every": "1d", "last_run": None, "outcome": None}],
            },
        )

    def test_should_refuse_a_machine_with_no_operational_corpus(self):
        # Arrange
        runtime = create_runtime(self.root)

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(SimpleNamespace(), runtime)

        # Assert
        self.assertEqual(str(raised.exception), "the operational corpus is missing; run brigade init first")
