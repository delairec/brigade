import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.order_answer import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses

RUN_ID = "20261019T090000Z-aaaaaa"
TARGET = "@RESULT.nightly_20261019T090000Z_aaaaaa"
ORDER_RECORD = {
    "schema_version": 1,
    "order": {
        "name": "nightly",
        "recipe": "triage",
        "project": None,
        "text": None,
        "params": [],
        "every": None,
        "output": None,
        "status": "active",
    },
    "recipe": {
        "name": "triage",
        "max_wall": 30,
        "steps": [
            {"kind": "collect", "collector": "open-issues"},
            {"kind": "judge", "slot": "judging", "procedure": "triage", "answer": "RESULT"},
        ],
    },
}
FILLED_FIELDS = {
    "fields": [{"name": "ORDER", "atoms": ['"nightly"']}, {"name": "RUN", "atoms": ['"20261019T090000Z-aaaaaa"']}]
}
CHANGED_FIELDS = {
    "fields": [{"name": "ORDER", "atoms": ['"daily"']}, {"name": "RUN", "atoms": ['"20261019T090000Z-aaaaaa"']}]
}
ANSWER_TEXT = 'RESULT nightly_20261019T090000Z_aaaaaa\n\tORDER "nightly"\n\tRUN "20261019T090000Z-aaaaaa"\n'


class OrderAnswerTextTest(unittest.TestCase):
    def test_should_say_that_the_answer_of_the_run_is_recorded(self):
        # Act
        text = COMMAND.render_text({"schema_version": 1, "run": RUN_ID, "answer": "/runs/answer.awawa"})

        # Assert
        self.assertEqual(text, f"the answer of run {RUN_ID} recorded")


class OrderAnswerOfAJudgeStepTest(unittest.TestCase):
    def setUp(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        self.processes = ScriptedProcesses()
        self.runtime = create_test_runtime(create_test_paths(root), run_process=self.processes)
        self.run_directory = self.runtime.paths.state_root / "runs" / RUN_ID
        (self.run_directory / "steps").mkdir(parents=True)
        (self.run_directory / "order.json").write_text(json.dumps(ORDER_RECORD), encoding="utf-8")
        (self.run_directory / "steps" / "1-collect.json").write_text(
            json.dumps({"skipped": "no issue"}), encoding="utf-8"
        )
        self.answer_file = root / "answer.awawa"
        self.answer_file.write_text(ANSWER_TEXT, encoding="utf-8")
        validation = self.run_directory / "validation"
        self.processes.answer(("awawa", "lint", "--strict", str(validation / "submitted")))
        self.submitted_show = ("awawa", "show", TARGET, "--json", str(validation / "submitted"))
        self.processes.answer_json(("awawa", "show", TARGET, "--json", str(validation / "filled")), FILLED_FIELDS)

    def test_should_record_an_answer_the_schema_of_its_judge_step_accepts(self):
        # Arrange
        self.processes.answer_json(self.submitted_show, FILLED_FIELDS)

        # Act
        document = COMMAND.run(Namespace(run=RUN_ID, file=str(self.answer_file)), self.runtime)

        # Assert
        self.assertEqual(
            document, {"schema_version": 1, "run": RUN_ID, "answer": str(self.run_directory / "answer.awawa")}
        )
        self.assertEqual((self.run_directory / "answer.awawa").read_text(encoding="utf-8"), ANSWER_TEXT)

    def test_should_keep_no_answer_that_changed_the_order_brigade_filled(self):
        # Arrange
        self.processes.answer_json(self.submitted_show, CHANGED_FIELDS)

        # Act
        with self.assertRaises(BrigadeError):
            COMMAND.run(Namespace(run=RUN_ID, file=str(self.answer_file)), self.runtime)

        # Assert
        self.assertFalse((self.run_directory / "answer.awawa").exists())
