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
FILLED_FIELDS = [
    {"name": "STUDY", "atoms": ['"trees"']},
    {"name": "RUN", "atoms": [f'"{RUN_ID}"']},
]
SUBMITTED = 'FINDING trees_20261019T090000Z_aaaaaa\n\tSTUDY "trees"\n\tRUN "20261019T090000Z-aaaaaa"\n\tVERDICT "two"\n'


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

    def script_lint(self, exit_code: int, stdout: str = "") -> None:
        self.processes.answer(("awawa", "lint", "--strict", str(self.submitted)), exit_code=exit_code, stdout=stdout)

    def script_shown_fields(self, directory: Path, fields: list[dict]) -> None:
        self.processes.answer_json(
            ("awawa", "show", TARGET, "--json", str(directory)),
            {"fields": [*fields, {"name": "VERDICT", "atoms": ['"two"']}]},
        )

    def test_should_accept_an_answer_keeping_the_fields_brigade_filled(self):
        # Arrange
        self.script_lint(0)
        self.script_shown_fields(self.submitted, FILLED_FIELDS)
        self.script_shown_fields(self.filled, FILLED_FIELDS)

        # Act
        validate_answer(self.runtime, STUDY, self.run_directory, SUBMITTED)

        # Assert
        self.assertFalse((self.run_directory / "validation").exists())

    def test_should_refuse_an_answer_that_changed_a_field_brigade_filled(self):
        # Arrange
        self.script_lint(0)
        self.script_shown_fields(self.submitted, [FILLED_FIELDS[0], {"name": "RUN", "atoms": ['"another"']}])
        self.script_shown_fields(self.filled, FILLED_FIELDS)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            validate_answer(self.runtime, STUDY, self.run_directory, SUBMITTED)

        # Assert
        self.assertEqual(str(refusal.exception), "the answer changed RUN, a field brigade filled")

    def test_should_refuse_an_answer_the_schema_rejects_with_its_diagnostics(self):
        # Arrange
        self.script_lint(1, "answer.awawa:4: L003 unknown field VERDIKT\n")

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            validate_answer(self.runtime, STUDY, self.run_directory, SUBMITTED)

        # Assert
        self.assertEqual(
            (str(refusal.exception), (self.run_directory / "validation").exists()),
            ("the schema of FINDING rejects the answer\nanswer.awawa:4: L003 unknown field VERDIKT", False),
        )

    def test_should_refuse_an_answer_that_holds_no_entity_of_the_run(self):
        # Arrange
        self.script_lint(0)
        self.processes.answer(("awawa", "show", TARGET, "--json", str(self.submitted)), exit_code=1)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            validate_answer(self.runtime, STUDY, self.run_directory, SUBMITTED)

        # Assert
        self.assertEqual(str(refusal.exception), f"the answer holds no {TARGET}")

    def test_should_check_the_submitted_answer_against_the_operational_schema(self):
        # Arrange
        (self.root / "config" / "_schema.awawa").write_text("SCHEMA FINDING\n", encoding="utf-8")
        copies = []

        def read_the_linted_corpus(request) -> tuple[int, str, str]:
            schema = (self.submitted / "_schema.awawa").read_text(encoding="utf-8")
            copies.append((schema, (self.submitted / "answer.awawa").read_text(encoding="utf-8")))
            return 1, "", ""

        self.processes.answer_by(("awawa", "lint", "--strict", str(self.submitted)), read_the_linted_corpus)

        # Act
        with self.assertRaises(BrigadeError):
            validate_answer(self.runtime, STUDY, self.run_directory, SUBMITTED)

        # Assert
        self.assertEqual(copies, [("SCHEMA FINDING\n", SUBMITTED)])
