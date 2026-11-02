import contextlib
import json
import tempfile
import unittest
from argparse import Namespace
from datetime import UTC, datetime
from pathlib import Path

from brigade.commands.study_run import COMMAND
from brigade.errors import BrigadeError
from brigade.ledger.append_event import append_event
from brigade.system.resolve_collector import resolve_collector
from tests.unit.commands.command_runtime import create_corpus_double, write_ledger, write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.mining.create_run_finished import create_run_finished
from tests.unit.mining.transcripts_client_double import TranscriptsClientDouble
from tests.unit.plugin_double import PluginDouble

RUN_ID = "20261019T090000Z-e10d04"
NO_STUDY_RECORDED = {}
IN_THE_WINDOW = datetime(2026, 10, 18, 8, 0, tzinfo=UTC)
SESSION_BRIEF = {
    "role": "user",
    "timestamp": None,
    "content": "Deliver B42.",
    "tool_calls": 0,
    "id": None,
    "usage": None,
}
SESSION_CORRECTION = {**SESSION_BRIEF, "content": "Not that file: the spec."}


def _resolve_any_plugin(kind: str, name: str, **places):
    return PluginDouble(kind=kind, name=name)


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
        options = Namespace(name="health", run_id=None)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class StudyRunOfAStudyTest(unittest.TestCase):
    def test_should_refuse_a_study_the_operational_corpus_does_not_define(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        runtime = create_test_runtime(
            create_test_paths(root),
            run_process=create_corpus_double(NO_STUDY_RECORDED),
            resolve_plugin=_resolve_any_plugin,
        )

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(name="health", run_id=None), runtime)

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
        runtime = create_test_runtime(
            create_test_paths(root),
            run_process=create_corpus_double(NO_STUDY_RECORDED),
            resolve_plugin=_resolve_any_plugin,
        )

        # Act
        ending = COMMAND.run(Namespace(name="wave-report", run_id=RUN_ID), runtime)

        # Assert
        self.assertEqual(ending, {"schema_version": 1, "study": "wave-report", "run": RUN_ID, "state": "done"})


class StudyRunOfMineTranscriptsTest(unittest.TestCase):
    def test_should_collect_the_findings_of_the_sessions_through_the_client_adapter_each_run_names(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.enterContext(contextlib.chdir(root))
        write_operational_corpus(root)
        processes = create_corpus_double(NO_STUDY_RECORDED)
        plugins = {
            ("client", "vibe"): TranscriptsClientDouble({"s-built": [SESSION_BRIEF, SESSION_CORRECTION]}),
            ("forge", "github"): PluginDouble(kind="forge", name="github"),
            ("document", "awawa"): PluginDouble(kind="document", name="awawa"),
        }
        runtime = create_test_runtime(
            create_test_paths(root),
            run_process=processes,
            resolve_plugin=lambda kind, name, **options: (
                resolve_collector(name, options["places"]) if kind == "collector" else plugins[kind, name]
            ),
        )
        run_directory = runtime.paths.state_root / "runs" / "r3"
        run_directory.mkdir(parents=True)
        (run_directory / "run.json").write_text('{"run": "r3", "worktree": "/srv/oak/.brigade/worktrees/B42"}')
        append_event(runtime.paths, IN_THE_WINDOW, create_run_finished("r3", "s-built"))

        # Act
        ending = COMMAND.run(Namespace(name="mine_transcripts", run_id=None), runtime)

        # Assert
        collected = json.loads(
            (runtime.paths.state_root / "runs" / ending["run"] / "steps" / "collect.json").read_text()
        )
        self.assertEqual(
            collected["collected"][0]["summary"],
            {"sessions": 1, "findings": {"correction": 1}, "unreadable": []},
        )
