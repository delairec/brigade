import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from brigade.commands.study_run import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import (
    create_corpus_double,
    create_runtime,
    write_ledger,
    write_operational_corpus,
)

RUN_ID = "20261019T090000Z-e10d04"
NO_STUDY_RECORDED = {}


def _resolve_any_plugin(kind: str, name: str, **places):
    return SimpleNamespace(kind=kind, name=name)


class StudyRunTextTest(unittest.TestCase):
    def test_should_say_where_the_run_ended(self):
        # Arrange
        rows = [
            ("a run done", {"state": "done"}, f"@STUDY.health run {RUN_ID} done"),
            (
                "a run parked",
                {"state": "parked", "step": "judge", "reason": "the slot answered nothing"},
                f"@STUDY.health run {RUN_ID} parked at judge: the slot answered nothing",
            ),
        ]
        for case, ending, expected_text in rows:
            with self.subTest(case=case):
                # Act
                text = COMMAND.render_text({"schema_version": 1, "study": "health", "run": RUN_ID, **ending})

                # Assert
                self.assertEqual(text, expected_text)


class StudyRunExitCodeTest(unittest.TestCase):
    def test_should_fail_on_a_parked_run_only(self):
        # Arrange
        rows = [("a run done", "done", 0), ("a run parked", "parked", 1)]
        for case, state, expected_exit_code in rows:
            with self.subTest(case=case):
                # Act
                exit_code = COMMAND.decide_exit_code({"schema_version": 1, "state": state})

                # Assert
                self.assertEqual(exit_code, expected_exit_code)


class StudyRunRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = SimpleNamespace(name="health", run_id=None)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class StudyRunOfAStudyTest(unittest.TestCase):
    def test_should_refuse_a_study_the_operational_corpus_does_not_define(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        runtime = create_runtime(
            root, run_process=create_corpus_double(NO_STUDY_RECORDED), resolve_plugin=_resolve_any_plugin
        )

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(SimpleNamespace(name="health", run_id=None), runtime)

        # Assert
        self.assertEqual(str(raised.exception), "@STUDY.health is not defined in the operational corpus")

    def test_should_resume_the_run_of_a_wave_report_from_the_wave_its_run_records(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        write_ledger(
            root,
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-19T08:00:00Z",
                    "event": "wave.started",
                    "wave": "oak_w2",
                    "project": "oak",
                    "branch": "integration/oak_w2",
                    "tasks": ["B17"],
                }
            ],
        )
        steps = root / "state" / "runs" / RUN_ID / "steps"
        steps.mkdir(parents=True)
        (steps.parent / "study.json").write_text(
            '{"schema_version": 1, "study": "wave-report", "project": "oak", "wave": "oak_w2"}', encoding="utf-8"
        )
        (steps / "collect.json").write_text("{}", encoding="utf-8")
        (steps / "judge.json").write_text("{}", encoding="utf-8")
        (steps / "output.json").write_text("{}", encoding="utf-8")
        runtime = create_runtime(
            root, run_process=create_corpus_double(NO_STUDY_RECORDED), resolve_plugin=_resolve_any_plugin
        )

        # Act
        ending = COMMAND.run(SimpleNamespace(name="wave-report", run_id=RUN_ID), runtime)

        # Assert
        self.assertEqual(ending, {"schema_version": 1, "study": "wave-report", "run": RUN_ID, "state": "done"})
