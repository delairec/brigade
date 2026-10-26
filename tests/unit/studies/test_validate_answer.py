import dataclasses
import json
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.studies.convert_study import Study
from brigade.studies.validate_answer import validate_answer
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
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

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
REPORT_STUDY = dataclasses.replace(STUDY, name="wave-report", project="oak", answer_type="REPORT", wave="oak_w2")
REPORT_TARGET = "@REPORT.oak_w2"
LEDGER_ITEMS = [
    {"ts": "2026-10-04T08:00:00Z", "event": "wave.started", "wave": "oak_w2", "tasks": ["B17"]},
    {"ts": "2026-10-04T10:30:00Z", "event": "task.state", "wave": "oak_w2", "task": "B17", "state": "merged"},
]
DIAGNOSTICS = "answer.awawa:4: L003 unknown field VERDIKT\n"
TRIAGE = dataclasses.replace(
    STUDY, name="triage", collectors=("inbox-families",), slot="triage", output="entity:PATTERN", answer_type="PATTERN"
)
RATIFIED_PATTERN = 'PATTERN cli_is_hard_to_read\n\tTITLE "the cli is hard to read"\n\tSTATUS ratified\n'
SUBMITTED_PATTERN = 'PATTERN slow_tick\n\tTITLE "the tick is slow"\n\tSTATUS dismissed\n\tACTION dismiss\n'


class ValidateAnswerTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()
        write_operational_corpus(self.root)
        self.runtime = create_test_runtime(create_test_paths(self.root), run_process=self.processes)
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

    def write_document(self, collector: str, items: list) -> dict:
        path = self.root / f"{collector}.json"
        path.write_text(json.dumps({"collector": collector, "items": items}), encoding="utf-8")
        return {"collector": collector, "summary": {}, "document": str(path)}

    def script_report_answer(self, submitted_fields: dict, filled_fields: dict) -> None:
        collected = [
            self.write_document("ledger", LEDGER_ITEMS),
            self.write_document("pr-list", []),
            self.write_document("corpus", []),
            self.write_document("git-diff-stat", []),
        ]
        (self.run_directory / "steps" / "collect.json").write_text(
            json.dumps({"collected": collected}), encoding="utf-8"
        )
        self.processes.answer_entities(
            self.runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"), ("CORPUS", "corpus"))}
        )
        self.processes.answer_entities(self.runtime.paths.config_root, "REQUEST", {})
        self.processes.answer(("awawa", "lint", "--strict", str(self.submitted)))
        self.processes.answer_json(("awawa", "show", REPORT_TARGET, "--json", str(self.submitted)), submitted_fields)
        self.processes.answer_json(("awawa", "show", REPORT_TARGET, "--json", str(self.filled)), filled_fields)

    def test_should_refuse_a_report_that_changed_a_field_brigade_filled(self):
        for field, refusal_message in [
            ("WAVE", "the answer changed WAVE, a field brigade filled"),
            ("PROJECT", "the answer changed PROJECT, a field brigade filled"),
            ("TASK_ROW", "the answer changed TASK_ROW, a field brigade filled"),
            ("STATISTIC", "the answer changed STATISTIC, a field brigade filled"),
            ("GRAPH", "the answer changed GRAPH, a field brigade filled"),
            ("MANUAL_TEST", "the answer changed MANUAL_TEST, a field brigade filled"),
            ("INSTRUCTIONS_CHANGE", "the answer changed INSTRUCTIONS_CHANGE, a field brigade filled"),
            ("PARKED_QUESTION", "the answer changed PARKED_QUESTION, a field brigade filled"),
        ]:
            with self.subTest(field=field):
                # Arrange
                self.script_report_answer(
                    {"fields": [{"name": field, "atoms": ['"rewritten by the slot"']}]},
                    {"fields": [{"name": field, "atoms": ['"filled by brigade"']}]},
                )

                # Act
                with self.assertRaises(BrigadeError) as refusal:
                    validate_answer(self.runtime, REPORT_STUDY, self.run_directory, SUBMITTED)

                # Assert
                self.assertEqual(str(refusal.exception), refusal_message)

    def test_should_accept_a_report_whose_slot_completed_the_prose_brigade_left_to_it(self):
        for field in ["NARRATIVE", "REASON", "TESTER_STEP", "SAMPLING"]:
            with self.subTest(field=field):
                # Arrange
                self.script_report_answer(
                    {"fields": [{"name": field, "atoms": ['"written by the slot"']}]},
                    {"fields": [{"name": field, "atoms": ['"left to the slot"']}]},
                )

                # Act
                accepted = validate_answer(self.runtime, REPORT_STUDY, self.run_directory, SUBMITTED)

                # Assert
                self.assertIsNone(accepted)


class ValidateTriageAnswerTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()
        write_operational_corpus(self.root)
        self.runtime = create_test_runtime(create_test_paths(self.root), run_process=self.processes)
        self.run_directory = self.root / "state" / "runs" / RUN_ID
        (self.run_directory / "steps").mkdir(parents=True)
        (self.run_directory / "steps" / "collect.json").write_text('{"collected": []}', encoding="utf-8")
        self.submitted = self.run_directory / "validation" / "submitted"
        self.answered = self.run_directory / "validation" / "answered"

    def test_should_lint_the_patterns_beside_those_the_operational_corpus_holds(self):
        # Arrange
        (self.root / "config" / "patterns.awawa").write_text(RATIFIED_PATTERN, encoding="utf-8")
        linted = []

        def record_the_patterns_linted(request):
            linted.append((self.submitted / "patterns.awawa").read_text(encoding="utf-8"))
            return 0, "", ""

        self.processes.answer_by(("awawa", "lint", "--strict", str(self.submitted)), record_the_patterns_linted)
        no_patterns_in_the_answer = {}
        self.processes.answer_entities(self.answered, "PATTERN", no_patterns_in_the_answer)

        # Act
        validate_answer(self.runtime, TRIAGE, self.run_directory, "")

        # Assert
        self.assertEqual(linted, [RATIFIED_PATTERN])

    def test_should_check_the_patterns_of_the_answer_and_leave_out_those_the_operational_corpus_holds(self):
        # Arrange
        (self.root / "config" / "patterns.awawa").write_text(RATIFIED_PATTERN, encoding="utf-8")
        self.processes.answer(("awawa", "lint", "--strict", str(self.submitted)))
        self.processes.answer_entities(
            self.submitted,
            "PATTERN",
            {"cli_is_hard_to_read": (("TITLE", "the cli is hard to read"), ("STATUS", "ratified"))},
        )
        no_patterns_in_the_answer = {}
        self.processes.answer_entities(self.answered, "PATTERN", no_patterns_in_the_answer)

        # Act
        accepted = validate_answer(self.runtime, TRIAGE, self.run_directory, "")

        # Assert
        self.assertIsNone(accepted)

    def test_should_refuse_a_triage_answer_its_patterns_check_refuses(self):
        # Arrange
        self.processes.answer(("awawa", "lint", "--strict", str(self.submitted)))
        self.processes.answer_entities(
            self.answered,
            "PATTERN",
            {"slow_tick": (("TITLE", "the tick is slow"), ("STATUS", "dismissed"), ("ACTION", "dismiss"))},
        )

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            validate_answer(self.runtime, TRIAGE, self.run_directory, SUBMITTED_PATTERN)

        # Assert
        self.assertEqual(str(refusal.exception), "@PATTERN.slow_tick is dismissed: a triage proposes it new")
