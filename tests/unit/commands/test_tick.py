import contextlib
import dataclasses
import fcntl
import io
import json
import os
import signal
import tempfile
import time
import unittest
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from brigade.commands.tick import COMMAND
from brigade.errors import StandingDown, UsageError
from brigade.runtime import Runtime
from brigade.system.paths import Paths
from brigade.system.trail_writer import TrailWriter

LOOP_MODE = "loop"
NO_PATH_NEEDED = ""
WAKE_THE_LOOP = signal.SIGUSR1


def _report_nothing(trace) -> None:
    pass


def _refuse_process(request):
    raise AssertionError(f"a round of tick ran {request.argv}")


def _refuse_resolution(kind: str, name: str):
    raise AssertionError(f"a round of tick resolved the {kind} plugin {name}")


def _ignore_signal(_received, _frame) -> None:
    pass


def _create_runtime(root: Path, now: datetime) -> Runtime:
    return Runtime(
        run_process=_refuse_process,
        spawn_process=_refuse_process,
        paths=Paths(
            config_root=root / "config",
            state_root=root / "state",
            cache_root=root / "cache",
            home=root / "home",
            executable_search_path=NO_PATH_NEEDED,
        ),
        now=now,
        read_clock=lambda: now,
        entry_point=root / "bin" / "brigade",
        trail=TrailWriter(_report_nothing),
        resolve_plugin=_refuse_resolution,
    )


def _stop_the_loop_it_entered() -> Runtime:
    os.kill(os.getpid(), signal.SIGTERM)
    raise AssertionError("brigade tick entered the loop")


def _create_round_factory(rounds: list[tuple[Runtime, signal.Signals]]):
    remaining = iter(rounds)

    def create_runtime() -> Runtime:
        runtime, signal_to_receive = next(remaining)
        os.kill(os.getpid(), signal_to_receive)
        return runtime

    return create_runtime


class TickLoopTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        previous_handler = signal.signal(WAKE_THE_LOOP, _ignore_signal)
        self.addCleanup(signal.signal, signal.SIGUSR1, previous_handler)

    def test_should_give_each_round_a_runtime_of_its_own(self):
        # Arrange
        first_round = _create_runtime(self.root, datetime(2026, 10, 7, 9, 0, 0, tzinfo=UTC))
        second_round = _create_runtime(self.root, datetime(2026, 10, 7, 9, 5, 0, tzinfo=UTC))
        request = SimpleNamespace(
            mode=LOOP_MODE,
            create_runtime=_create_round_factory([(first_round, WAKE_THE_LOOP), (second_round, signal.SIGTERM)]),
        )
        command_runtime = _create_runtime(self.root, datetime(2026, 10, 7, 8, 59, 0, tzinfo=UTC))

        # Act
        with contextlib.redirect_stderr(io.StringIO()):
            COMMAND.run(request, command_runtime)

        # Assert
        self.assertCountEqual(
            (self.root / "state" / "ticks").iterdir(),
            [
                self.root / "state" / "ticks" / "20261007T090000Z.jsonl",
                self.root / "state" / "ticks" / "20261007T090500Z.jsonl",
            ],
        )


class TickWithoutAKnownModeTest(unittest.TestCase):
    def test_should_refuse_the_mode_without_entering_the_loop(self):
        # Arrange
        rows = [
            (None, "unknown mode None: --once, --dry-run or --loop"),
            ("weekly", "unknown mode 'weekly': --once, --dry-run or --loop"),
        ]
        for mode, expected_message in rows:
            with self.subTest(mode=mode):
                # Arrange
                directory = self.enterContext(tempfile.TemporaryDirectory())
                runtime = _create_runtime(Path(directory), datetime(2026, 10, 7, 9, 0, 0, tzinfo=UTC))
                request = SimpleNamespace(mode=mode, create_runtime=_stop_the_loop_it_entered)

                # Act
                with self.assertRaises(UsageError) as raised, contextlib.redirect_stderr(io.StringIO()):
                    COMMAND.run(request, runtime)

                # Assert
                self.assertEqual(str(raised.exception), expected_message)


def _resolve_a_forge(kind: str, name: str, **places):
    return SimpleNamespace(kind=kind, name=name)


def _create_quiet_runtime(root: Path) -> Runtime:
    return dataclasses.replace(
        _create_runtime(root, datetime(2026, 10, 7, 9, 0, 0, tzinfo=UTC)), resolve_plugin=_resolve_a_forge
    )


def _create_single_round_factory(runtime: Runtime):
    def create_runtime() -> Runtime:
        os.kill(os.getpid(), signal.SIGTERM)
        return runtime

    return create_runtime


class TickOnAnEmptyMachineTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.lock = self.root / "state" / "locks" / "tick.lock"

    def test_should_apply_no_action_and_write_the_heartbeat(self):
        # Arrange
        request = SimpleNamespace(mode="once")

        # Act
        with mock.patch.object(time, "monotonic", side_effect=[100.0, 100.25]):
            document = COMMAND.run(request, _create_quiet_runtime(self.root))

        # Assert
        self.assertEqual(
            (document, json.loads((self.root / "state" / "tick.json").read_text(encoding="utf-8"))),
            (
                {
                    "schema_version": 1,
                    "mode": "once",
                    "ts": "2026-10-07T09:00:00Z",
                    "duration_ms": 250,
                    "actions_applied": 0,
                    "heartbeat": str(self.root / "state" / "tick.json"),
                },
                {"schema_version": 1, "ts": "2026-10-07T09:00:00Z", "duration_ms": 250, "actions_applied": 0},
            ),
        )

    def test_should_stand_down_while_another_tick_holds_the_lock(self):
        # Arrange
        request = SimpleNamespace(mode="once")
        self.lock.parent.mkdir(parents=True)

        # Act
        with self.lock.open("a") as held, self.assertRaises(StandingDown) as raised:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            COMMAND.run(request, _create_quiet_runtime(self.root))

        # Assert
        self.assertEqual(str(raised.exception), f"another tick holds {self.lock}")

    def test_should_plan_nothing_on_a_dry_run(self):
        # Arrange
        request = SimpleNamespace(mode="dry-run")

        # Act
        document = COMMAND.run(request, _create_quiet_runtime(self.root))

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "mode": "dry-run",
                "snapshot": {
                    "schema_version": 1,
                    "now": "2026-10-07T09:00:00Z",
                    "waves": [],
                    "planned": [],
                    "projects": [],
                    "rate_limits": [],
                    "studies": [],
                    "live_study_runs": [],
                    "study_runs": 2,
                },
                "plan": [],
            },
        )

    def test_should_report_each_round_of_the_loop_on_stderr(self):
        # Arrange
        create_round = _create_single_round_factory(_create_quiet_runtime(self.root))
        request = SimpleNamespace(mode=LOOP_MODE, create_runtime=create_round)
        reported = io.StringIO()

        # Act
        with contextlib.redirect_stderr(reported), mock.patch.object(time, "monotonic", side_effect=[100.0, 100.25]):
            document = COMMAND.run(request, _create_quiet_runtime(self.root))

        # Assert
        self.assertEqual(
            (document, reported.getvalue()),
            (
                {"schema_version": 1, "mode": "loop", "ticks_attempted": 1},
                "brigade tick: 2026-10-07T09:00:00Z: 0 actions applied in 250 ms\n",
            ),
        )

    def test_should_report_a_round_of_the_loop_another_tick_holds(self):
        # Arrange
        create_round = _create_single_round_factory(_create_quiet_runtime(self.root))
        request = SimpleNamespace(mode=LOOP_MODE, create_runtime=create_round)
        self.lock.parent.mkdir(parents=True)
        reported = io.StringIO()

        # Act
        with self.lock.open("a") as held, contextlib.redirect_stderr(reported):
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            COMMAND.run(request, _create_quiet_runtime(self.root))

        # Assert
        self.assertEqual(reported.getvalue(), f"brigade tick: another tick holds {self.lock}\n")


class TickTextTest(unittest.TestCase):
    def test_should_render_each_mode(self):
        # Arrange
        rows = [
            (
                "once",
                {"mode": "once", "ts": "2026-10-07T09:00:00Z", "duration_ms": 250, "actions_applied": 2},
                "tick 2026-10-07T09:00:00Z: 2 actions applied in 250 ms",
            ),
            ("a loop", {"mode": "loop", "ticks_attempted": 3}, "tick --loop: 3 ticks attempted"),
            (
                "a dry run planning nothing",
                {"mode": "dry-run", "snapshot": {"schema_version": 1, "now": "2026-10-07T09:00:00Z"}, "plan": []},
                "snapshot\n  now  2026-10-07T09:00:00Z\nplan\n  no action",
            ),
            (
                "a dry run planning an action",
                {"mode": "dry-run", "snapshot": {}, "plan": [{"wave": "tidepool_w16"}]},
                "snapshot\nplan\n  {'wave': 'tidepool_w16'}",
            ),
        ]
        for case, document, expected_text in rows:
            with self.subTest(case=case):
                # Act
                text = COMMAND.render_text(document)

                # Assert
                self.assertEqual(text, expected_text)


class TickExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"mode": "once"})

        # Assert
        self.assertEqual(exit_code, 0)


class TickRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = SimpleNamespace(mode="once")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)
