import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.order_context import COMMAND
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses

RUN_ID = "20261019T090000Z-aaaaaa"
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
RESULT_SCHEMA = "SCHEMA RESULT\n\tFIELD NARRATIVE string\n"
SKELETON = (
    "RESULT nightly_20261019T090000Z_aaaaaa\n"
    '\tORDER "nightly"\n'
    '\tRUN "20261019T090000Z-aaaaaa"\n'
    '\tCOLLECTED "open-issues"\n'
    '\t\tSUMMARY "{\\"open\\": 2}"\n'
    '\t\tDOCUMENT "/srv/open/document.json"\n'
)


class OrderContextTextTest(unittest.TestCase):
    def test_should_print_the_documents_the_skeleton_and_the_schema(self):
        # Arrange
        document = {
            "schema_version": 1,
            "order": "nightly",
            "run": RUN_ID,
            "collected": [{"collector": "open-issues", "summary": {"open": 2}, "document": "/srv/document.json"}],
            "answer": "RESULT nightly\n",
            "schema": "SCHEMA RESULT\n",
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            f"order: nightly, run {RUN_ID}\nopen-issues: {{\"open\": 2}}, /srv/document.json\n\nRESULT nightly\n\nSCHEMA RESULT",
        )


class OrderContextOfAJudgeStepTest(unittest.TestCase):
    def test_should_hand_the_documents_of_the_run_and_the_schema_of_the_answer(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        processes = ScriptedProcesses()
        runtime = create_test_runtime(create_test_paths(root), run_process=processes)
        processes.answer(("awawa", "show", "RESULT", str(runtime.paths.config_root)), stdout=RESULT_SCHEMA)
        run_directory = runtime.paths.state_root / "runs" / RUN_ID
        (run_directory / "steps").mkdir(parents=True)
        (run_directory / "order.json").write_text(json.dumps(ORDER_RECORD), encoding="utf-8")
        collected = {"collector": "open-issues", "summary": {"open": 2}, "document": "/srv/open/document.json"}
        (run_directory / "steps" / "1-collect.json").write_text(json.dumps(collected), encoding="utf-8")

        # Act
        document = COMMAND.run(Namespace(run=RUN_ID), runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "order": "nightly",
                "run": RUN_ID,
                "collected": [
                    {"collector": "open-issues", "summary": {"open": 2}, "document": "/srv/open/document.json"}
                ],
                "answer": SKELETON,
                "schema": RESULT_SCHEMA,
            },
        )
