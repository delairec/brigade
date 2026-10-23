import argparse
import functools
import json
import os
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

from brigade.adapters.documents import markdown
from brigade.commands.run import COMMAND, run
from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.system.resolve_plugin import PluginSources, resolve_plugin
from tests.unit.commands.run_doubles import (
    CLIENT_AND_DOCUMENT_CONFIGURATION,
    CLOCK_PROBE,
    STEP_COUNTING_PROBE,
    create_plugin_resolution,
    spawn_as_this_process,
)
from tests.unit.create_test_paths import NO_SEARCH_PATH, create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.refuse_to_run import refuse_to_run

UNKNOWN_CLIENT = "no-such-client"
UNKNOWN_PROCEDURE = "no-such-procedure"


def _create_runtime(root: Path) -> Runtime:
    sources = PluginSources(executable_search_path=NO_SEARCH_PATH, run_process=refuse_to_run)
    return create_test_runtime(
        create_test_paths(root), resolve_plugin=functools.partial(resolve_plugin, sources=sources)
    )


class RunClientPrecedenceTest(unittest.TestCase):
    def test_should_report_an_unknown_client_before_an_unknown_procedure(self):
        # Arrange
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        (root / "config").mkdir()
        (root / "config" / "config.toml").write_text(f'client = "{UNKNOWN_CLIENT}"\n', encoding="utf-8")
        request = Namespace(
            procedure=UNKNOWN_PROCEDURE,
            slot="build",
            project=None,
            cwd=None,
            brief=None,
            arguments=(),
            run_id=None,
            wave=None,
            task=None,
            detach=False,
            resume=False,
        )

        # Act
        with self.assertRaises(BrigadeError) as raised:
            run(request, _create_runtime(root))

        # Assert
        self.assertEqual(
            str(raised.exception),
            f"no client adapter {UNKNOWN_CLIENT}: no built-in module and no brigade-client-{UNKNOWN_CLIENT} on PATH",
        )


class RunTextTest(unittest.TestCase):
    def test_should_count_the_segments_of_a_run_handed_over(self):
        # Arrange
        document = {
            "run": "20261007T090000Z-b70a01",
            "procedure": "deliver",
            "role": "builder",
            "slot": "build",
            "outcome": "done",
            "segments": 2,
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "run 20261007T090000Z-b70a01: deliver as builder (build) done after 2 segments")


class RunExtraArgumentTest(unittest.TestCase):
    def test_should_leave_every_word_but_an_option_to_the_procedure(self):
        # Arrange
        rows = [
            ("an argument of the procedure", "task=B06", True),
            ("an unknown option", "--frobnicate", False),
            ("a word with no separator", "B06", True),
        ]
        for case, extra, expected_acceptance in rows:
            with self.subTest(case=case):
                # Act
                accepted = COMMAND.accept_extra_argument(extra)

                # Assert
                self.assertIs(accepted, expected_acceptance)


class RunTextOfOneSegmentTest(unittest.TestCase):
    def test_should_name_the_single_segment_of_a_run(self):
        # Arrange
        document = {
            "run": "20261007T090000Z-b70a01",
            "procedure": "deliver",
            "role": "builder",
            "slot": "build",
            "outcome": "failed",
            "segments": 1,
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "run 20261007T090000Z-b70a01: deliver as builder (build) failed after 1 segment")

    def test_should_print_the_run_id_alone_for_a_detached_run(self):
        # Act
        text = COMMAND.render_text({"schema_version": 1, "run": "20261007T090000Z-b70a01", "pid": 4242})

        # Assert
        self.assertEqual(text, "20261007T090000Z-b70a01")


class RunExitCodeTest(unittest.TestCase):
    def test_should_exit_on_the_outcome_of_the_run(self):
        # Arrange
        rows = [
            ("a detached run", {"run": "20261007T090000Z-b70a01", "pid": 4242}, 0),
            ("a run done", {"outcome": "done"}, 0),
            ("a run stopped", {"outcome": "stopped"}, 21),
        ]
        for case, document, expected_exit_code in rows:
            with self.subTest(case=case):
                # Act
                exit_code = COMMAND.decide_exit_code(document)

                # Assert
                self.assertEqual(exit_code, expected_exit_code)


class RunDiagnosticsTest(unittest.TestCase):
    def test_should_pass_on_the_warnings_of_the_run(self):
        # Arrange
        rows = [
            ("no warning", {"run": "20261007T090000Z-b70a01"}, []),
            ("a warning", {"run": "20261007T090000Z-b70a01", "warnings": ["no steps"]}, ["no steps"]),
        ]
        for case, document, expected_diagnostics in rows:
            with self.subTest(case=case):
                # Act
                diagnostics = COMMAND.describe_diagnostics(document)

                # Assert
                self.assertEqual(diagnostics, expected_diagnostics)


class RunRequestTest(unittest.TestCase):
    def test_should_hand_the_extra_words_to_the_procedure_as_its_arguments(self):
        # Arrange
        options = argparse.Namespace(procedure="deliver", extra_arguments=["task=B06"])

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertEqual(
            request, argparse.Namespace(procedure="deliver", extra_arguments=["task=B06"], arguments=["task=B06"])
        )


class RunDetachedTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "config").mkdir()
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        self.request = Namespace(
            procedure="wave-plan",
            slot="plan",
            project=None,
            cwd=str(self.root),
            brief=None,
            arguments=("request=tidepool_1",),
            run_id="20261019T090000Z-a1b2c3",
            wave=None,
            task=None,
            detach=True,
            resume=False,
        )

    def test_should_record_the_run_and_hand_it_to_a_process_of_its_own(self):
        # Arrange
        this_process = os.getpid()
        runtime = create_test_runtime(
            create_test_paths(self.root),
            spawn_process=spawn_as_this_process,
            resolve_plugin=create_plugin_resolution(STEP_COUNTING_PROBE),
        )

        # Act
        document = run(self.request, runtime)

        # Assert
        record = json.loads(
            (self.root / "state" / "runs" / "20261019T090000Z-a1b2c3" / "run.json").read_text(encoding="utf-8")
        )
        self.assertEqual(document, {"schema_version": 1, "run": "20261019T090000Z-a1b2c3", "pid": this_process})
        self.assertEqual(record["procedure"], "wave-plan")
        self.assertEqual(record["arguments"], {"request": "tidepool_1"})

    def test_should_warn_that_a_client_counting_no_steps_holds_the_budget_on_the_clock(self):
        # Arrange
        runtime = create_test_runtime(
            create_test_paths(self.root),
            spawn_process=spawn_as_this_process,
            resolve_plugin=create_plugin_resolution(CLOCK_PROBE),
        )

        # Act
        document = run(self.request, runtime)

        # Assert
        self.assertEqual(
            document["warnings"],
            [
                "double counts no steps: the budget of 30 steps is held on the clock and the run cut at its limit of 1140 s"
            ],
        )


class ClientDeliveringTheTaskDouble:
    def answer(self, operation: str, request: dict) -> dict:
        if operation == "probe":
            return STEP_COUNTING_PROBE
        if operation == "launch-argv":
            return {
                "schema_version": 1,
                "argv": ["double-client", "--print"],
                "environment": {},
                "stdin": request["brief"],
                "session_id": None,
            }
        return {
            "schema_version": 1,
            "outcome": "done",
            "steps": 12,
            "usage": None,
            "session_id": "session-b74",
            "duration_ms": 4200,
            "cost_usd": None,
            "error_class": None,
            "reset": None,
            "message": "the task is delivered",
        }


class ExitedClientDouble:
    pid = 4242

    def wait(self, **_limit) -> int:
        return 0


def _spawn_a_client_that_exits(request):
    request.stdout.write_text("the client delivered the task\n", encoding="utf-8")
    request.stderr.write_text("", encoding="utf-8")
    return ExitedClientDouble()


def _resolve_the_delivering_client(kind: str, name: str, **places):
    plugins = {"client": ClientDeliveringTheTaskDouble(), "document": markdown, "forge": SimpleNamespace()}
    return plugins[kind]


class RunAttachedTest(unittest.TestCase):
    def test_should_run_the_client_to_its_end_and_report_its_outcome(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (root / "config").mkdir()
        (root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        request = Namespace(
            procedure="build-task",
            slot="build",
            project=None,
            cwd=str(root),
            brief=None,
            arguments=("task=@TASK.T7",),
            run_id="20261019T090000Z-a1b2c3",
            wave=None,
            task=None,
            detach=False,
            resume=False,
        )
        runtime = create_test_runtime(
            create_test_paths(root),
            spawn_process=_spawn_a_client_that_exits,
            resolve_plugin=_resolve_the_delivering_client,
        )

        # Act
        document = run(request, runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "run": "20261019T090000Z-a1b2c3",
                "procedure": "build-task",
                "slot": "build",
                "role": "builder",
                "client": "double",
                "project": None,
                "segments": 1,
                "outcome": "done",
            },
        )
