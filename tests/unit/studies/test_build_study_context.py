import json
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.studies.build_study_context import build_study_context
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses

RUN_ID = "20261019T090000Z-aaaaaa"
STUDY_FIELDS = (
    ("QUESTION", "how many trees?"),
    ("SLOT", "review"),
    ("OUTPUT", "entity:FINDING"),
    ("ANSWER", "FINDING"),
    ("STATUS", "active"),
)
COLLECTED = '{"collected": [{"collector": "weather", "summary": {"days": 1}, "document": "/srv/document.json"}]}'
PACKAGE = {
    "schema_version": 1,
    "study": "trees",
    "run": RUN_ID,
    "question": "how many trees?",
    "collected": [{"collector": "weather", "summary": {"days": 1}, "document": "/srv/document.json"}],
    "answer": (
        "FINDING trees_20261019T090000Z_aaaaaa\n"
        '\tSTUDY "trees"\n'
        '\tRUN "20261019T090000Z-aaaaaa"\n'
        '\tCOLLECTED "weather"\n'
        '\t\tSUMMARY "{\\"days\\": 1}"\n'
        '\t\tDOCUMENT "/srv/document.json"\n'
    ),
    "prose_fields": ["VERDICT"],
    "schema": "SCHEMA FINDING\n",
}


class BuildStudyContextTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(self.root, self.processes)
        self.run_directory = self.root / "state" / "runs" / RUN_ID
        (self.run_directory / "steps").mkdir(parents=True)

    def script_study_run(self) -> None:
        config_root = self.runtime.paths.config_root
        (self.run_directory / "study.json").write_text('{"study": "trees"}', encoding="utf-8")
        (self.run_directory / "steps" / "collect.json").write_text(COLLECTED, encoding="utf-8")
        self.processes.answer_entity(config_root, "STUDY", "trees", STUDY_FIELDS)
        self.processes.answer_json(
            ("awawa", "show", "FINDING", "--json", str(config_root)),
            {
                "fields": [
                    {"name": "FIELD", "atoms": ["STUDY", "string"]},
                    {"name": "FIELD", "atoms": ["VERDICT", "string"]},
                    {"name": "DESC", "atoms": ['"a finding"']},
                ]
            },
        )
        self.processes.answer(("awawa", "show", "FINDING", str(config_root)), stdout="SCHEMA FINDING\n")

    def test_should_package_the_question_the_evidence_and_the_answer_to_complete(self):
        # Arrange
        self.script_study_run()

        # Act
        package = build_study_context(self.runtime, RUN_ID)

        # Assert
        self.assertEqual(package, PACKAGE)

    def test_should_keep_the_package_in_the_run(self):
        # Arrange
        self.script_study_run()

        # Act
        build_study_context(self.runtime, RUN_ID)

        # Assert
        self.assertEqual(json.loads((self.run_directory / "context.json").read_text(encoding="utf-8")), PACKAGE)

    def test_should_refuse_a_run_that_is_not_a_run_of_a_study(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            build_study_context(self.runtime, RUN_ID)

        # Assert
        self.assertEqual(str(refusal.exception), f"{RUN_ID} is not a run of a study")

    def test_should_refuse_a_run_that_collected_no_evidence_yet(self):
        # Arrange
        (self.run_directory / "study.json").write_text('{"study": "trees"}', encoding="utf-8")
        self.processes.answer_entity(self.runtime.paths.config_root, "STUDY", "trees", STUDY_FIELDS)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            build_study_context(self.runtime, RUN_ID)

        # Assert
        self.assertEqual(str(refusal.exception), f"the run {RUN_ID} has collected no evidence yet")
