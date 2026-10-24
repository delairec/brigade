import argparse
import contextlib
import functools
import io
import itertools
import json
import os
import signal
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.adapters.documents import markdown
from brigade.add_command_parsers import add_command_parsers
from brigade.commands.run import COMMAND, run
from brigade.errors import BrigadeError, ToolFailure
from brigade.runtime import Runtime
from brigade.system.resolve_plugin import PluginSources, resolve_plugin
from brigade.system.run_process import ProcessRequest
from tests.unit.commands.run_doubles import (
    CLIENT_AND_DOCUMENT_CONFIGURATION,
    CLOCK_PROBE,
    STEP_COUNTING_PROBE,
    create_plugin_resolution,
    spawn_as_this_process,
)
from tests.unit.create_test_paths import NO_SEARCH_PATH, create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.plugin_double import PluginDouble
from tests.unit.refuse_to_run import refuse_to_run
from tests.unit.runs.write_run_record import write_run_record
from tests.unit.runs.write_run_result import write_run_result

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

    def test_should_write_the_spawned_run_in_the_trail_of_its_run(self):
        # Arrange
        this_process = os.getpid()
        runtime = create_test_runtime(
            create_test_paths(self.root),
            spawn_process=spawn_as_this_process,
            resolve_plugin=create_plugin_resolution(STEP_COUNTING_PROBE),
        )

        # Act
        run(self.request, runtime)

        # Assert
        self.assertEqual(
            json.loads(
                (self.root / "state" / "runs" / "20261019T090000Z-a1b2c3" / "processes.jsonl").read_text(
                    encoding="utf-8"
                )
            ),
            {
                "schema_version": 1,
                "argv": [
                    sys.executable,
                    "/srv/brigade/bin/brigade",
                    "run",
                    "wave-plan",
                    "request=tidepool_1",
                    "--slot",
                    "plan",
                    "--cwd",
                    str(self.root),
                    "--run-id",
                    "20261019T090000Z-a1b2c3",
                ],
                "cwd": str(self.root),
                "exit": None,
                "duration_ms": None,
                "outcome": "spawned",
                "pid": this_process,
            },
        )

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
    plugins = {
        "client": ClientDeliveringTheTaskDouble(),
        "document": markdown,
        "forge": PluginDouble(kind="forge", name="github"),
    }
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

    def test_should_append_its_records_to_the_trail_the_process_that_detached_it_began(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (root / "config").mkdir()
        (root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        trail = root / "state" / "runs" / "20261019T090000Z-a1b2c3" / "processes.jsonl"
        trail.parent.mkdir(parents=True)
        trail.write_text('{"outcome": "spawned"}\n', encoding="utf-8")
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
        run(request, runtime)

        # Assert
        self.assertEqual(
            trail.read_text(encoding="utf-8"),
            '{"outcome": "spawned"}\n'
            f'{{"schema_version": 1, "argv": ["double-client", "--print"], "cwd": "{root}", "exit": 0,'
            ' "duration_ms": 0, "outcome": "exited"}\n',
        )


class RunAttachedBoundingTheRunsTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.root / "config").mkdir()
        (self.root / "config" / "config.toml").write_text(
            f"runs_kept = 1\n{CLIENT_AND_DOCUMENT_CONFIGURATION}", encoding="utf-8"
        )
        self.runs = self.root / "state" / "runs"

    def run_attached(self) -> dict:
        request = Namespace(
            procedure="build-task",
            slot="build",
            project=None,
            cwd=str(self.root),
            brief=None,
            arguments=("task=@TASK.T7",),
            run_id="20261019T090000Z-a1b2c3",
            wave=None,
            task=None,
            detach=False,
            resume=False,
        )
        runtime = create_test_runtime(
            create_test_paths(self.root),
            spawn_process=_spawn_a_client_that_exits,
            resolve_plugin=_resolve_the_delivering_client,
        )
        return run(request, runtime)

    def test_should_remove_the_oldest_finished_run_beyond_the_runs_kept_of_the_configuration(self):
        # Arrange
        write_run_result(self.runs / "20261018T090000Z-0ld001" / "result.json")
        write_run_record(self.runs / "20261018T090000Z-0ld001")

        # Act
        self.run_attached()

        # Assert
        self.assertEqual(list(self.runs.iterdir()), [self.runs / "20261019T090000Z-a1b2c3"])

    def test_should_warn_of_an_unreadable_run_it_skipped(self):
        # Arrange
        (self.runs / "20261018T090000Z-unread").mkdir(parents=True)
        (self.runs / "20261018T090000Z-unread" / "run.json").write_text("not json", encoding="utf-8")

        unreadable_record = self.runs / "20261018T090000Z-unread" / "run.json"

        # Act
        document = self.run_attached()

        # Assert
        self.assertEqual(
            document["warnings"],
            [f"run 20261018T090000Z-unread skipped, {unreadable_record} is not a run record: not a JSON document"],
        )


PID_HELD_BY_NO_PROCESS = 2**31 - 1


class ClientInterruptedWhileItRunsDouble:
    pid = PID_HELD_BY_NO_PROCESS

    def __init__(self):
        self._answers = itertools.chain([self._interrupt_brigade], itertools.repeat(self._end_stopped))

    def wait(self, timeout: float) -> int:
        return next(self._answers)(timeout)

    def _interrupt_brigade(self, timeout: float) -> int:
        os.kill(os.getpid(), signal.SIGINT)
        raise subprocess.TimeoutExpired("double-client", timeout)

    def _end_stopped(self, _timeout: float) -> int:
        return -signal.SIGTERM


def _spawn_a_client_interrupted_while_it_runs(request):
    request.stdout.write_text("Reading the task\n", encoding="utf-8")
    request.stderr.write_text("", encoding="utf-8")
    return ClientInterruptedWhileItRunsDouble()


class RunAttachedInterruptedTest(unittest.TestCase):
    def test_should_stop_the_client_and_report_the_run_stopped(self):
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
            spawn_process=_spawn_a_client_interrupted_while_it_runs,
            resolve_plugin=_resolve_the_delivering_client,
        )

        # Act
        document = run(request, runtime)

        # Assert
        self.assertEqual(document["outcome"], "stopped")


def _fail_awawa(request: ProcessRequest):
    raise ToolFailure("awawa show @AGENT.reviewer --json /srv/instructions exited 2: awawa: unreadable root")


class RunOfASlotBoundInAnUnreadableInstructionsCorpusTest(unittest.TestCase):
    def test_should_refuse_the_run_before_launching_any_client(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (root / "config").mkdir()
        (root / "config" / "config.toml").write_text(
            f'{CLIENT_AND_DOCUMENT_CONFIGURATION}instructions = "/srv/instructions"\n[slots]\nbuild = "reviewer"\n',
            encoding="utf-8",
        )
        request = Namespace(
            procedure="build-task",
            slot="build",
            project=None,
            cwd=str(root),
            brief=None,
            arguments=(),
            run_id="20261019T090000Z-a1b2c3",
            wave=None,
            task=None,
            detach=False,
            resume=False,
        )
        runtime = create_test_runtime(
            create_test_paths(root), run_process=_fail_awawa, resolve_plugin=_resolve_the_delivering_client
        )

        # Act
        with self.assertRaises(ToolFailure) as refusal:
            run(request, runtime)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "awawa show @AGENT.reviewer --json /srv/instructions exited 2: awawa: unreadable root",
        )


def _create_run_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="brigade")
    add_command_parsers(parser, [COMMAND], argparse.ArgumentParser(add_help=False))
    return parser


class RunParserTest(unittest.TestCase):
    def test_should_leave_the_procedure_every_key_value_argument_wherever_it_stands_among_the_options(self):
        # Arrange
        rows = [
            ("after the options", ["run", "build-task", "--slot", "build", "a=1", "b=2"]),
            ("before the options", ["run", "build-task", "a=1", "b=2", "--slot", "build"]),
            ("on both sides of an option", ["run", "build-task", "a=1", "--slot", "build", "b=2"]),
        ]
        for case, words in rows:
            with self.subTest(case=case):
                # Act
                options, extras = _create_run_parser().parse_known_args(words)

                # Assert
                self.assertEqual(options.procedure, "build-task")
                self.assertEqual(options.slot, "build")
                self.assertEqual(extras, ["a=1", "b=2"])

    def test_should_name_the_key_value_arguments_of_the_procedure_in_its_help(self):
        # Arrange
        page = io.StringIO()

        # Act
        with contextlib.suppress(SystemExit), contextlib.redirect_stdout(page):
            _create_run_parser().parse_args(["run", "--help"])

        # Assert
        self.assertIn("key=value words, follow it before or after the options", " ".join(page.getvalue().split()))
