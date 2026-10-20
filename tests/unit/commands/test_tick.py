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
from unittest.mock import ANY

from brigade.commands.tick import COMMAND
from brigade.errors import StandingDown, UsageError
from brigade.runtime import Runtime
from brigade.system.paths import Paths
from brigade.system.trail_writer import TrailWriter
from tests.unit.commands.command_runtime import (
    create_machine_double,
    create_runtime,
    write_ledger,
    write_operational_corpus,
)
from tests.unit.commands.run_directories import FIRST_RUN, create_run_record, create_run_result, write_run
from tests.unit.commands.run_doubles import (
    CLIENT_AND_DOCUMENT_CONFIGURATION,
    STEP_COUNTING_PROBE,
    create_plugin_resolution,
)

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
                    "projects": [],
                    "studies": [],
                    "live_study_runs": [],
                    "study_runs": 2,
                    "rate_limits": [],
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


WAVE = "tidepool_w16"
WAVE_BRANCH = "integration/M4"
WAVE_HEAD = "8885daa"
TASK_TO_DELIVER = (("MILESTONE", "@MILESTONE.M4"), ("STATUS", "todo"))
TASK_DELIVERED = (("MILESTONE", "@MILESTONE.M4"), ("STATUS", "implemented"), ("DELIVERED_BY", "42"))
MACHINE_OUTPUTS = {
    ("git", "rev-parse", "--verify"): f"{WAVE_HEAD}\n",
    ("git", "cat-file", "-p"): ".brigade/worktrees/\n",
    ("git", "worktree", "add"): "",
    ("git", "merge-base"): "",
    ("git", "fetch"): "",
    ("git", "diff"): "",
    ("awawa", "status", "TASK", "--where", "STATUS==implemented"): '{"entities": []}',
    ("awawa", "refs"): '{"incoming": []}',
    ("awawa", "fmt"): "",
    ("awawa", "lint"): "",
    ("awawa", "diff"): '{"added": [], "changed": [], "removed": []}',
}
WAVE_STARTED = {
    "schema_version": 2,
    "ts": "2026-10-18T09:00:00Z",
    "event": "wave.started",
    "wave": "tidepool_w16",
    "project": "tidepool",
    "branch": "integration/M4",
    "tasks": ["T7"],
}
TASK_PR_OPENED = {
    "schema_version": 1,
    "ts": "2026-10-18T11:00:00Z",
    "event": "task.pr_opened",
    "project": "tidepool",
    "task": "T7",
    "wave": "tidepool_w16",
    "branch": "task/M4/T7",
    "pr": 42,
    "login": "tidepool-bot",
}
NO_PULL_REQUEST = None
OPEN_PULL_REQUEST = {
    "number": 42,
    "state": "open",
    "checks": [{"name": "ci", "verdict": "pass"}],
    "review": None,
    "behind": False,
    "head": "8885daa",
}
MERGED_PULL_REQUEST = {**OPEN_PULL_REQUEST, "state": "merged"}
TASK_PREFLIGHTED_AT_THE_HEAD = {
    "schema_version": 1,
    "ts": "2026-10-18T11:30:00Z",
    "event": "task.preflighted",
    "project": "tidepool",
    "wave": "tidepool_w16",
    "task": "T7",
    "pr": 42,
    "head": "8885daa",
    "checks": [],
}
NO_DETAILS_ASKED = None
PULL_REQUEST_DETAILS = {
    "head": "task/M4/T7",
    "head_sha": "8885daa",
    "checks": [{"name": "ci", "verdict": "success"}],
    "body": "Delivers @TASK.T7.",
}
HEALTH_STUDY = (
    ("TITLE", "the health of the machine"),
    ("COLLECTOR", "runs-list"),
    ("SLOT", "report"),
    ("EVERY", "daily@06:00"),
    ("OUTPUT", "file:/home/user/health.md"),
    ("ANSWER", "ANSWER"),
    ("STATUS", "active"),
)


def _record_task_state(state: str) -> dict:
    return {
        "schema_version": 1,
        "ts": "2026-10-18T10:00:00Z",
        "event": "task.state",
        "wave": "tidepool_w16",
        "task": "T7",
        "state": state,
    }


class ForgeDouble:
    def __init__(self, found: dict | None, details: dict | None):
        self.found = found
        self.details = details

    def find_pull_request(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "pull_request": self.found}

    def read_pull_request(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "pull_request": self.details}


class SpawnRecorderDouble:
    def __init__(self):
        self.argvs = []

    def spawn(self, request):
        self.argvs.append(request.argv[2:])
        return SimpleNamespace(pid=os.getpid())


class TickApplyingTheActionsOfAWaveTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        self.repository = self.root / "tidepool"
        self.worktree = self.repository / ".brigade" / "worktrees" / "T7"
        self.spawn = SpawnRecorderDouble()

    def _create_runtime(self, task: tuple, forge: ForgeDouble) -> Runtime:
        corpus = {
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"))},
            "TASK": {"T7": task},
        }
        return create_runtime(
            self.root,
            run_process=create_machine_double(corpus, MACHINE_OUTPUTS),
            spawn_process=self.spawn.spawn,
            resolve_plugin=create_plugin_resolution(STEP_COUNTING_PROBE, forge),
        )

    def _read_event(self, rank: int) -> dict:
        return json.loads(
            (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8").splitlines()[rank]
        )

    def _read_last_event(self) -> dict:
        return self._read_event(-1)

    def test_should_launch_the_build_run_of_a_task_ready_to_start(self):
        # Arrange
        self.worktree.mkdir(parents=True)
        write_ledger(self.root, [WAVE_STARTED])
        runtime = self._create_runtime(TASK_TO_DELIVER, ForgeDouble(NO_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        document = COMMAND.run(SimpleNamespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            (document["actions_applied"], self.spawn.argvs),
            (
                1,
                [
                    (
                        "run",
                        "build-task",
                        "task=@TASK.T7",
                        "base=integration/M4",
                        "--slot",
                        "build",
                        "--cwd",
                        str(self.worktree),
                        "--project",
                        "tidepool",
                        "--brief",
                        str(self.root / "state" / "briefs" / "tidepool_w16-T7.md"),
                        "--wave",
                        "tidepool_w16",
                        "--task",
                        "T7",
                        "--run-id",
                        ANY,
                    )
                ],
            ),
        )

    def test_should_resume_the_run_of_a_task_paused_on_the_quota(self):
        # Arrange
        self.worktree.mkdir(parents=True)
        stopped_run = {
            **create_run_record(FIRST_RUN, WAVE, "T7"),
            "procedure_path": "build-task",
            "project": "tidepool",
            "cwd": str(self.worktree),
        }
        write_run(self.root / "state", stopped_run, create_run_result(FIRST_RUN, "failed", "2026-10-18T10:00:00Z"))
        finished = {**create_run_result(FIRST_RUN, "failed", "2026-10-18T10:00:00Z"), "wave": WAVE, "task": "T7"}
        write_ledger(self.root, [WAVE_STARTED, finished, _record_task_state("paused:quota")])
        runtime = self._create_runtime(TASK_TO_DELIVER, ForgeDouble(NO_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self.spawn.argvs,
            [
                (
                    "run",
                    "build-task",
                    "--slot",
                    "build",
                    "--cwd",
                    str(self.worktree),
                    "--project",
                    "tidepool",
                    "--wave",
                    "tidepool_w16",
                    "--task",
                    "T7",
                    "--run-id",
                    FIRST_RUN,
                    "--resume",
                )
            ],
        )

    def test_should_record_the_merge_of_the_pull_request_of_a_running_task(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("running")])
        runtime = self._create_runtime(TASK_DELIVERED, ForgeDouble(MERGED_PULL_REQUEST, NO_DETAILS_ASKED))
        first_event_of_the_tick = 2

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_event(first_event_of_the_tick),
            {
                "schema_version": 1,
                "ts": "2026-10-19T09:00:00Z",
                "event": "task.state",
                "wave": "tidepool_w16",
                "task": "T7",
                "state": "merged",
            },
        )

    def test_should_hold_for_verification_a_pull_request_passing_its_preflight(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("pr_open"), TASK_PR_OPENED])
        runtime = self._create_runtime(TASK_DELIVERED, ForgeDouble(OPEN_PULL_REQUEST, PULL_REQUEST_DETAILS))

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_last_event(),
            {
                "schema_version": 1,
                "ts": "2026-10-19T09:00:00Z",
                "event": "task.state",
                "wave": "tidepool_w16",
                "task": "T7",
                "state": "verifying",
            },
        )

    def test_should_launch_the_verification_of_a_task_in_verifying(self):
        # Arrange
        self.worktree.mkdir(parents=True)
        write_ledger(
            self.root, [WAVE_STARTED, TASK_PR_OPENED, TASK_PREFLIGHTED_AT_THE_HEAD, _record_task_state("verifying")]
        )
        runtime = self._create_runtime(TASK_DELIVERED, ForgeDouble(OPEN_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self.spawn.argvs,
            [
                (
                    "run",
                    "verify-pr",
                    "pr=42",
                    "task=@TASK.T7",
                    "--slot",
                    "review",
                    "--cwd",
                    str(self.worktree),
                    "--project",
                    "tidepool",
                    "--wave",
                    "tidepool_w16",
                    "--task",
                    "T7",
                    "--run-id",
                    ANY,
                )
            ],
        )

    def test_should_record_the_verdict_passed_at_the_head_of_the_pull_request(self):
        # Arrange
        verdict = {
            "schema_version": 1,
            "ts": "2026-10-18T12:00:00Z",
            "event": "task.verdict",
            "project": "tidepool",
            "wave": "tidepool_w16",
            "task": "T7",
            "pr": 42,
            "head": "8885daa",
            "verdict": "pass",
            "findings": [],
            "login": None,
        }
        write_ledger(
            self.root,
            [WAVE_STARTED, TASK_PR_OPENED, TASK_PREFLIGHTED_AT_THE_HEAD, _record_task_state("verifying"), verdict],
        )
        runtime = self._create_runtime(TASK_DELIVERED, ForgeDouble(OPEN_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_last_event(),
            {
                "schema_version": 1,
                "ts": "2026-10-19T09:00:00Z",
                "event": "task.state",
                "wave": "tidepool_w16",
                "task": "T7",
                "state": "verified",
            },
        )

    def test_should_leave_open_a_pull_request_failing_its_preflight(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("pr_open"), TASK_PR_OPENED])
        failing_checks = {**PULL_REQUEST_DETAILS, "checks": [{"name": "ci", "verdict": "failure"}]}
        runtime = self._create_runtime(TASK_DELIVERED, ForgeDouble(OPEN_PULL_REQUEST, failing_checks))

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), runtime)

        # Assert
        self.assertEqual(self._read_last_event()["event"], "task.preflighted")


class TickLaunchingAStudyTest(unittest.TestCase):
    def test_should_launch_a_study_whose_schedule_is_due(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        spawn = SpawnRecorderDouble()
        runtime = create_runtime(
            root,
            run_process=create_machine_double({"STUDY": {"health": HEALTH_STUDY}}, MACHINE_OUTPUTS),
            spawn_process=spawn.spawn,
            resolve_plugin=create_plugin_resolution(STEP_COUNTING_PROBE),
        )

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), runtime)

        # Assert
        self.assertEqual(spawn.argvs, [("study", "run", "health", "--run-id", ANY)])
