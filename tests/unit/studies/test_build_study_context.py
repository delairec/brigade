import json
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.ledger.append_event import append_event
from brigade.ledger.wave_started import WaveStarted
from brigade.studies.build_study_context import build_study_context
from tests.unit.create_scripted_runtime import RUNTIME_NOW, create_scripted_runtime
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

LEDGER_ITEMS = [
    {"ts": "2026-10-04T08:00:00Z", "event": "wave.started", "wave": "oak_w2", "tasks": ["B17"]},
    {"ts": "2026-10-04T10:30:00Z", "event": "task.state", "wave": "oak_w2", "task": "B17", "state": "merged"},
]
REPORT_ANSWER = (
    "REPORT oak_w2\n"
    '\tWAVE "oak_w2"\n'
    '\tPROJECT "oak"\n'
    '\tTASK_ROW "B17 merged"\n'
    '\tSTATISTIC "tasks 1"\n'
    '\tSTATISTIC "merged 1"\n'
    '\tSTATISTIC "parked 0"\n'
    '\tSTATISTIC "runs 0"\n'
    '\tSTATISTIC "files 0"\n'
    '\tSTATISTIC "insertions 0"\n'
    '\tSTATISTIC "deletions 0"\n'
)


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

    def write_document(self, collector: str, items: list) -> dict:
        path = self.run_directory / f"{collector}.json"
        path.write_text(json.dumps({"collector": collector, "items": items}), encoding="utf-8")
        return {"collector": collector, "summary": {}, "document": str(path)}

    def script_wave_report_run(self) -> list[dict]:
        config_root = self.runtime.paths.config_root
        append_event(
            self.runtime.paths,
            RUNTIME_NOW,
            WaveStarted(wave="oak_w2", project="oak", branch="integration/oak_w2", tasks=("B17",)),
        )
        (self.run_directory / "study.json").write_text(
            '{"study": "wave-report", "project": "oak", "wave": "oak_w2"}', encoding="utf-8"
        )
        collected = [
            self.write_document("ledger", LEDGER_ITEMS),
            self.write_document("pr-list", []),
            self.write_document("corpus", []),
            self.write_document("git-diff-stat", []),
        ]
        (self.run_directory / "steps" / "collect.json").write_text(
            json.dumps({"collected": collected}), encoding="utf-8"
        )
        self.processes.answer_entities(config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"), ("CORPUS", "corpus"))})
        self.processes.answer_json(
            ("awawa", "show", "REPORT", "--json", str(config_root)),
            {
                "fields": [
                    {"name": "FIELD", "atoms": ["WAVE", "string"]},
                    {"name": "FIELD", "atoms": ["TASK_ROW", "string"]},
                    {"name": "FIELD", "atoms": ["NARRATIVE", "string"]},
                ]
            },
        )
        self.processes.answer(("awawa", "show", "REPORT", str(config_root)), stdout="SCHEMA REPORT\n")
        return collected

    def test_should_package_the_report_of_the_wave_to_complete(self):
        # Arrange
        collected = self.script_wave_report_run()

        # Act
        package = build_study_context(self.runtime, RUN_ID)

        # Assert
        self.assertEqual(
            package,
            {
                "schema_version": 1,
                "study": "wave-report",
                "run": RUN_ID,
                "question": (
                    "Complete the report of the wave oak_w2: what happened, why each parked or failed task stopped,"
                    " how a tester checks each manual test, and which changes are worth reading by sampling."
                ),
                "collected": collected,
                "answer": REPORT_ANSWER,
                "prose_fields": ["NARRATIVE"],
                "schema": "SCHEMA REPORT\n",
            },
        )
