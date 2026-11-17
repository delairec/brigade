import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.recipes.run_order import OrderRun
from brigade.recipes.validate_result import validate_result
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses

RUN_ID = "20261019T090000Z-aaaaaa"
TARGET = "@RESULT.nightly_20261019T090000Z_aaaaaa"
FILLED_FIELDS = {
    "fields": [
        {"name": "ORDER", "atoms": ['"nightly"']},
        {"name": "RUN", "atoms": ['"20261019T090000Z-aaaaaa"']},
        {"name": "NARRATIVE", "atoms": ['"two issues stand open"']},
    ]
}
CHANGED_FIELDS = {
    "fields": [
        {"name": "ORDER", "atoms": ['"nightly"']},
        {"name": "RUN", "atoms": ['"another"']},
        {"name": "NARRATIVE", "atoms": ['"two issues stand open"']},
    ]
}
SUBMITTED = (
    'RESULT nightly_20261019T090000Z_aaaaaa\n\tORDER "nightly"\n\tRUN "20261019T090000Z-aaaaaa"\n'
    '\tNARRATIVE "two issues stand open"\n'
)
DIAGNOSTICS = "answer.awawa:4: L003 unknown field NARATIVE\n"


class ValidateResultTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        write_operational_corpus(root)
        self.processes = ScriptedProcesses()
        self.runtime = create_test_runtime(create_test_paths(root), run_process=self.processes)
        self.run_directory = root / "state" / "runs" / RUN_ID
        (self.run_directory / "steps").mkdir(parents=True)
        self.run = OrderRun(
            order="nightly",
            project=None,
            recipe={"name": "triage", "steps": [{"kind": "judge", "answer": "RESULT"}]},
            run_id=RUN_ID,
            run_directory=self.run_directory,
        )
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
        accepted = validate_result(self.runtime, self.run, SUBMITTED)

        # Assert
        self.assertIsNone(accepted)

    def test_should_remove_the_corpora_it_validated_in(self):
        # Arrange
        self.script_conforming_answer(FILLED_FIELDS)

        # Act
        validate_result(self.runtime, self.run, SUBMITTED)

        # Assert
        self.assertEqual(list(self.run_directory.iterdir()), [self.run_directory / "steps"])

    def test_should_refuse_an_answer_that_changed_a_field_brigade_filled(self):
        # Arrange
        self.script_conforming_answer(CHANGED_FIELDS)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            validate_result(self.runtime, self.run, SUBMITTED)

        # Assert
        self.assertEqual(str(refusal.exception), "the answer changed RUN, a field brigade filled")

    def test_should_refuse_an_answer_the_schema_its_judge_step_names_rejects(self):
        # Arrange
        self.processes.answer(("awawa", "lint", "--strict", str(self.submitted)), exit_code=1, stdout=DIAGNOSTICS)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            validate_result(self.runtime, self.run, SUBMITTED)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "the schema of RESULT rejects the answer\nanswer.awawa:4: L003 unknown field NARATIVE",
        )

    def test_should_refuse_an_answer_holding_no_result_of_the_run(self):
        # Arrange
        self.processes.answer(("awawa", "lint", "--strict", str(self.submitted)))
        self.processes.answer(("awawa", "show", TARGET, "--json", str(self.submitted)), exit_code=1)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            validate_result(self.runtime, self.run, SUBMITTED)

        # Assert
        self.assertEqual(str(refusal.exception), f"the answer holds no {TARGET}")
