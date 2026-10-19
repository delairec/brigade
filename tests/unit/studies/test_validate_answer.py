import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.studies.convert_study import Study
from brigade.studies.validate_answer import validate_answer
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses

RUN_ID = "20261019T090000Z-aaaaaa"
TARGET = "@FINDING.trees_20261019T090000Z_aaaaaa"
STUDY = Study(
    name="trees",
    project=None,
    question=None,
    collectors=(),
    slot="review",
    every=None,
    output="entity:FINDING",
    answer_type="FINDING",
    status="active",
)
FILLED_FIELDS = {
    "fields": [
        {"name": "STUDY", "atoms": ['"trees"']},
        {"name": "RUN", "atoms": ['"20261019T090000Z-aaaaaa"']},
        {"name": "VERDICT", "atoms": ['"two"']},
    ]
}
CHANGED_FIELDS = {
    "fields": [
        {"name": "STUDY", "atoms": ['"trees"']},
        {"name": "RUN", "atoms": ['"another"']},
        {"name": "VERDICT", "atoms": ['"two"']},
    ]
}
SUBMITTED = 'FINDING trees_20261019T090000Z_aaaaaa\n\tSTUDY "trees"\n\tRUN "20261019T090000Z-aaaaaa"\n\tVERDICT "two"\n'
DIAGNOSTICS = "answer.awawa:4: L003 unknown field VERDIKT\n"


class ValidateAnswerTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(self.root, self.processes)
        self.run_directory = self.root / "state" / "runs" / RUN_ID
        (self.run_directory / "steps").mkdir(parents=True)
        (self.run_directory / "steps" / "collect.json").write_text('{"collected": []}', encoding="utf-8")
        self.submitted = self.run_directory / "validation" / "submitted"
        self.filled = self.run_directory / "validation" / "filled"

    def script_conforming_answer(self, submitted_fields: dict) -> None:
        self.processes.answer(("awawa", "lint", "--strict", str(self.submitted)))
        self.processes.answer_json(("awawa", "show", TARGET, "--json", str(self.submitted)), submitted_fields)
        self.processes.answer_json(("awawa", "show", TARGET, "--json", str(self.filled)), FILLED_FIELDS)

    def test_should_accept_an_answer_keeping_the_fields_brigade_filled(self):
        # Arrange
        self.script_conforming_answer(FILLED_FIELDS)

        # Act
        accepted = validate_answer(self.runtime, STUDY, self.run_directory, SUBMITTED)

        # Assert
        self.assertIsNone(accepted)

    def test_should_remove_the_corpora_it_validated_in(self):
        # Arrange
        self.script_conforming_answer(FILLED_FIELDS)

        # Act
        validate_answer(self.runtime, STUDY, self.run_directory, SUBMITTED)

        # Assert
        self.assertEqual(list(self.run_directory.iterdir()), [self.run_directory / "steps"])

    def test_should_refuse_an_answer_that_changed_a_field_brigade_filled(self):
        # Arrange
        self.script_conforming_answer(CHANGED_FIELDS)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            validate_answer(self.runtime, STUDY, self.run_directory, SUBMITTED)

        # Assert
        self.assertEqual(str(refusal.exception), "the answer changed RUN, a field brigade filled")

    def test_should_refuse_an_answer_the_schema_rejects_with_its_diagnostics(self):
        # Arrange
        self.processes.answer(("awawa", "lint", "--strict", str(self.submitted)), exit_code=1, stdout=DIAGNOSTICS)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            validate_answer(self.runtime, STUDY, self.run_directory, SUBMITTED)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "the schema of FINDING rejects the answer\nanswer.awawa:4: L003 unknown field VERDIKT",
        )

    def test_should_remove_the_corpora_of_a_refused_answer(self):
        # Arrange
        self.processes.answer(("awawa", "lint", "--strict", str(self.submitted)), exit_code=1, stdout=DIAGNOSTICS)

        # Act
        with self.assertRaises(BrigadeError):
            validate_answer(self.runtime, STUDY, self.run_directory, SUBMITTED)

        # Assert
        self.assertEqual(list(self.run_directory.iterdir()), [self.run_directory / "steps"])

    def test_should_refuse_an_answer_that_holds_no_entity_of_the_run(self):
        # Arrange
        self.processes.answer(("awawa", "lint", "--strict", str(self.submitted)))
        self.processes.answer(("awawa", "show", TARGET, "--json", str(self.submitted)), exit_code=1)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            validate_answer(self.runtime, STUDY, self.run_directory, SUBMITTED)

        # Assert
        self.assertEqual(str(refusal.exception), f"the answer holds no {TARGET}")

    def test_should_check_the_submitted_answer_against_the_operational_schema(self):
        # Arrange
        (self.root / "config" / "_schema.awawa").write_text("SCHEMA FINDING\n", encoding="utf-8")
        linted = []

        def read_the_linted_corpus(request) -> tuple[int, str, str]:
            schema = (self.submitted / "_schema.awawa").read_text(encoding="utf-8")
            linted.append((schema, (self.submitted / "answer.awawa").read_text(encoding="utf-8")))
            return 1, "", ""

        self.processes.answer_by(("awawa", "lint", "--strict", str(self.submitted)), read_the_linted_corpus)

        # Act
        with self.assertRaises(BrigadeError):
            validate_answer(self.runtime, STUDY, self.run_directory, SUBMITTED)

        # Assert
        self.assertEqual(linted, [("SCHEMA FINDING\n", SUBMITTED)])
