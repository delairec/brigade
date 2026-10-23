import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.study_answer import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import create_machine_double, write_operational_corpus

RUN_ID = "20261019T090000Z-e10d04"
HEALTH_STUDY = (
    ("SLOT", "report"),
    ("OUTPUT", "file:/home/user/health.md"),
    ("ANSWER", "ANSWER"),
    ("STATUS", "active"),
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

ANSWER_TEXT = 'ANSWER health_20261019T090000Z_e10d04\n\tVERDICT "healthy"\n'
NO_FILLED_FIELD = json.dumps({"fields": []})


class StudyAnswerTextTest(unittest.TestCase):
    def test_should_say_that_the_answer_of_the_run_is_recorded(self):
        # Act
        text = COMMAND.render_text({"schema_version": 1, "run": RUN_ID, "answer": "/runs/answer.awawa"})

        # Assert
        self.assertEqual(text, f"the answer of run {RUN_ID} recorded")


class StudyAnswerExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1})

        # Assert
        self.assertEqual(exit_code, 0)


class StudyAnswerRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(run=RUN_ID, file="/home/user/answer.awawa")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class StudyAnswerOfAJudgingRunTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        write_operational_corpus(self.root)
        self.run_directory = self.root / "state" / "runs" / RUN_ID
        self.run_directory.mkdir(parents=True)
        (self.run_directory / "study.json").write_text(json.dumps({"study": "health"}), encoding="utf-8")
        (self.run_directory / "steps").mkdir()
        (self.run_directory / "steps" / "collect.json").write_text(json.dumps({"collected": []}), encoding="utf-8")
        outputs = {("awawa", "lint"): "", ("awawa", "show", "@ANSWER.health_20261019T090000Z_e10d04"): NO_FILLED_FIELD}
        self.runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=create_machine_double({"STUDY": {"health": HEALTH_STUDY}}, outputs),
        )

    def test_should_record_an_answer_the_schema_accepts(self):
        # Arrange
        answer_file = self.root / "answer.awawa"
        answer_file.write_text(ANSWER_TEXT, encoding="utf-8")

        # Act
        document = COMMAND.run(Namespace(run=RUN_ID, file=str(answer_file)), self.runtime)

        # Assert
        self.assertEqual(
            document, {"schema_version": 1, "run": RUN_ID, "answer": str(self.run_directory / "answer.awawa")}
        )
        self.assertEqual((self.run_directory / "answer.awawa").read_text(encoding="utf-8"), ANSWER_TEXT)

    def test_should_refuse_an_answer_file_it_cannot_read(self):
        # Arrange
        missing_file = self.root / "missing.awawa"

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(run=RUN_ID, file=str(missing_file)), self.runtime)

        # Assert
        self.assertEqual(str(raised.exception), f"cannot read {missing_file}: No such file or directory")
