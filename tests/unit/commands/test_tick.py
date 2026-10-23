import contextlib
import dataclasses
import fcntl
import io
import json
import os
import signal
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import ANY

from brigade.commands.tick import COMMAND
from brigade.errors import BrigadeError, StandingDown, UsageError
from brigade.runtime import Runtime
from brigade.system.paths import Paths
from brigade.system.trail_writer import TrailWriter
from tests.unit.commands.command_runtime import (
    ProcessAnswer,
    ScriptedProcessRunner,
    create_corpus_double,
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
from tests.unit.create_test_paths import PACKAGE_FILE

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
            package_file=PACKAGE_FILE,
        ),
        now=now,
        read_clock=lambda: now,
        read_monotonic=lambda: 0.0,
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

        runtime = dataclasses.replace(_create_quiet_runtime(self.root), read_monotonic=iter([100.0, 100.25]).__next__)

        # Act
        document = COMMAND.run(request, runtime)

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
                    "actions_failed": 0,
                    "heartbeat": str(self.root / "state" / "tick.json"),
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-07T09:00:00Z",
                    "duration_ms": 250,
                    "actions_applied": 0,
                    "actions_failed": 0,
                },
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
        create_round = _create_single_round_factory(
            dataclasses.replace(_create_quiet_runtime(self.root), read_monotonic=iter([100.0, 100.25]).__next__)
        )
        request = SimpleNamespace(mode=LOOP_MODE, create_runtime=create_round)
        reported = io.StringIO()

        # Act
        with contextlib.redirect_stderr(reported):
            document = COMMAND.run(request, _create_quiet_runtime(self.root))

        # Assert
        self.assertEqual(
            (document, reported.getvalue()),
            (
                {"schema_version": 1, "mode": "loop", "ticks_attempted": 1},
                "brigade tick: 2026-10-07T09:00:00Z: 0 actions applied, 0 failed in 250 ms\n",
            ),
        )

    def test_should_report_a_round_of_the_loop_another_tick_holds(self):
        # Arrange
        create_round = _create_single_round_factory(
            dataclasses.replace(_create_quiet_runtime(self.root), read_monotonic=iter([100.0, 100.25]).__next__)
        )
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
                {
                    "mode": "once",
                    "ts": "2026-10-07T09:00:00Z",
                    "duration_ms": 250,
                    "actions_applied": 2,
                    "actions_failed": 1,
                },
                "tick 2026-10-07T09:00:00Z: 2 actions applied, 1 failed in 250 ms",
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
    ("git", "worktree", "list"): "",
    ("git", "merge-base"): "",
    ("git", "fetch"): "",
    ("git", "diff"): "",
    ("git", "status", "--porcelain", "--untracked-files=no"): "",
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
WAVE_REPORTED = {
    "schema_version": 1,
    "ts": "2026-10-18T12:00:00Z",
    "event": "wave.reported",
    "wave": "tidepool_w16",
    "run": None,
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
BLOCKING_QUESTION_OUTPUTS = {
    ("awawa", "refs"): json.dumps(
        {
            "incoming": [
                {"from": {"type": "OPEN_QUESTION", "name": "Undecided", "status": "open"}, "field_path": ["BLOCKS"]}
            ]
        }
    ),
    ("awawa", "show", "OPEN_QUESTION"): json.dumps(
        {
            "fields": [
                {
                    "name": "FIELD",
                    "atoms": ["BLOCKS", "reference"],
                    "fields": [{"name": "CONVERSE", "atoms": ["BLOCKED_BY"], "fields": []}],
                }
            ]
        }
    ),
}
NO_PULL_REQUEST = None
OPEN_PULL_REQUEST = {
    "number": 42,
    "state": "open",
    "checks": [{"name": "ci", "verdict": "pass"}],
    "review": None,
    "behind": False,
    "head": "8885daa",
    "base": "integration/M4",
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
PULL_REQUEST_FAILING_TWO_CHECKS = {
    **OPEN_PULL_REQUEST,
    "checks": [{"name": "ci", "verdict": "failure"}, {"name": "coverage", "verdict": "failure"}],
}
TASK_PREFLIGHTED_ON_FAILING_CHECKS = {
    **TASK_PREFLIGHTED_AT_THE_HEAD,
    "checks": [{"name": "checks", "verdict": "fail", "findings": ["ci: failure", "coverage: failure"]}],
}
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
    def __init__(self, found: dict | None, details: dict | None, tails: dict | None = None):
        self.found = found
        self.details = details
        self.tails = tails
        self.check_log_requests = []

    def find_pull_request(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "pull_request": self.found}

    def read_pull_request(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "pull_request": self.details}

    def read_check_logs(self, request: dict, runtime) -> dict:
        self.check_log_requests.append(request)
        return {"schema_version": 1, "logs": [{"name": name, "tail": self.tails[name]} for name in request["checks"]]}


class SpawnReadingTheLedgerDouble:
    def __init__(self, ledger: Path):
        self.ledger = ledger
        self.last_events_at_spawn = []

    def spawn(self, request):
        self.last_events_at_spawn.append(json.loads(self.ledger.read_text(encoding="utf-8").splitlines()[-1]))
        return SimpleNamespace(pid=os.getpid())


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

    def _create_runtime(self, task: tuple, forge: ForgeDouble, setup: tuple = ()) -> Runtime:
        corpus = {
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"), *setup)},
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

    def test_should_record_the_task_running_before_its_build_run_is_spawned(self):
        # Arrange
        self.worktree.mkdir(parents=True)
        write_ledger(self.root, [WAVE_STARTED])
        self.spawn = SpawnReadingTheLedgerDouble(self.root / "state" / "ledger" / "2026-10.jsonl")
        runtime = self._create_runtime(TASK_TO_DELIVER, ForgeDouble(NO_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self.spawn.last_events_at_spawn,
            [
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "running",
                }
            ],
        )

    def test_should_record_a_failed_setup_as_a_failed_action_and_count_it_in_the_heartbeat(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED])
        broken_setup = (("SETUP", 'make "deps'),)
        runtime = self._create_runtime(TASK_TO_DELIVER, ForgeDouble(NO_PULL_REQUEST, NO_DETAILS_ASKED), broken_setup)
        first_event_of_the_tick = 1

        # Act
        document = COMMAND.run(SimpleNamespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            (
                document["actions_failed"],
                json.loads((self.root / "state" / "tick.json").read_text(encoding="utf-8"))["actions_failed"],
                self._read_event(first_event_of_the_tick + 1),
            ),
            (
                1,
                1,
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "tick.action_failed",
                    "action": "LaunchTask",
                    "project": "tidepool",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "error": 'the setup of @TASK.T7 failed: the line make "deps splits into no argv: No closing quotation',
                },
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

    def test_should_record_the_task_running_before_its_paused_run_is_resumed(self):
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
        self.spawn = SpawnReadingTheLedgerDouble(self.root / "state" / "ledger" / "2026-10.jsonl")
        runtime = self._create_runtime(TASK_TO_DELIVER, ForgeDouble(NO_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self.spawn.last_events_at_spawn,
            [
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "running",
                }
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

    def test_should_launch_the_remediation_of_a_task_in_changes_requested_and_record_it_in_fixing(self):
        # Arrange
        self.worktree.mkdir(parents=True)
        write_ledger(
            self.root,
            [WAVE_STARTED, TASK_PR_OPENED, TASK_PREFLIGHTED_AT_THE_HEAD, _record_task_state("changes_requested")],
        )
        runtime = self._create_runtime(TASK_DELIVERED, ForgeDouble(OPEN_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            (self.spawn.argvs, self._read_last_event()),
            (
                [
                    (
                        "run",
                        "remediate-pr",
                        "pr=42",
                        "task=@TASK.T7",
                        "--slot",
                        "remediate",
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
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "fixing",
                },
            ),
        )

    def test_should_ask_the_forge_for_the_last_200_lines_of_the_log_of_each_failing_check(self):
        # Arrange
        self.worktree.mkdir(parents=True)
        write_ledger(
            self.root,
            [WAVE_STARTED, TASK_PR_OPENED, TASK_PREFLIGHTED_ON_FAILING_CHECKS, _record_task_state("pr_open")],
        )
        forge = ForgeDouble(PULL_REQUEST_FAILING_TWO_CHECKS, NO_DETAILS_ASKED, {"ci": None, "coverage": None})
        runtime = self._create_runtime(TASK_DELIVERED, forge)

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), runtime)

        # Assert
        self.assertEqual(forge.check_log_requests[0]["lines"], 200)

    def test_should_launch_the_repair_of_the_failing_checks_with_the_tail_of_their_logs_and_record_it_in_fixing(self):
        # Arrange
        self.worktree.mkdir(parents=True)
        write_ledger(
            self.root,
            [WAVE_STARTED, TASK_PR_OPENED, TASK_PREFLIGHTED_ON_FAILING_CHECKS, _record_task_state("pr_open")],
        )
        tails = {"ci": "FAIL test_cart\nexit 1", "coverage": None}
        runtime = self._create_runtime(
            TASK_DELIVERED, ForgeDouble(PULL_REQUEST_FAILING_TWO_CHECKS, NO_DETAILS_ASKED, tails)
        )

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), runtime)

        # Assert
        brief = self.root / "state" / "briefs" / "tidepool_w16-T7-checks.md"
        self.assertEqual(
            (self.spawn.argvs, brief.read_text(), self._read_last_event()),
            (
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
                        str(brief),
                        "--wave",
                        "tidepool_w16",
                        "--task",
                        "T7",
                        "--run-id",
                        ANY,
                    )
                ],
                (
                    "Repair the failing checks of the pull request #42, which delivers @TASK.T7 of @PROJECT.tidepool,"
                    " in the wave tidepool_w16.\n"
                    "\n"
                    "- Base branch: integration/M4.\n"
                    f"- Worktree: {self.worktree}, on the branch task/M4/T7.\n"
                    "\n"
                    "The tail of the log of each failing check:\n"
                    "\n"
                    "## ci\n"
                    "\n"
                    "```\n"
                    "FAIL test_cart\n"
                    "exit 1\n"
                    "```\n"
                    "\n"
                    "## coverage\n"
                    "\n"
                    "The forge keeps no log of this check.\n"
                ),
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "fixing",
                },
            ),
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

    def test_should_park_a_queued_task_a_live_blocker_cites(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("queued")])
        corpus = {
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"))},
            "TASK": {"T7": TASK_TO_DELIVER},
        }
        runtime = create_runtime(
            self.root,
            run_process=create_machine_double(corpus, {**MACHINE_OUTPUTS, **BLOCKING_QUESTION_OUTPUTS}),
            spawn_process=self.spawn.spawn,
            resolve_plugin=create_plugin_resolution(
                STEP_COUNTING_PROBE, ForgeDouble(NO_PULL_REQUEST, NO_DETAILS_ASKED)
            ),
        )

        first_event_of_the_tick = 2

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_event(first_event_of_the_tick),
            {
                "schema_version": 1,
                "ts": "2026-10-19T09:00:00Z",
                "event": "task.parked",
                "wave": "tidepool_w16",
                "task": "T7",
                "reason": "blocked",
                "blockers": ["OPEN_QUESTION.Undecided"],
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

    def test_should_report_a_wave_whose_tasks_are_merged_or_parked(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("merged")])
        runtime = self._create_runtime(TASK_DELIVERED, ForgeDouble(NO_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_last_event(),
            {
                "schema_version": 1,
                "ts": "2026-10-19T09:00:00Z",
                "event": "wave.reported",
                "wave": "tidepool_w16",
                "run": ANY,
            },
        )

    def test_should_detach_the_wave_report_run_the_wave_reported_names(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("merged")])
        runtime = self._create_runtime(TASK_DELIVERED, ForgeDouble(NO_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), runtime)

        # Assert
        reported_run = self._read_last_event()["run"]
        self.assertEqual(self.spawn.argvs, [("study", "run", "wave-report", "--run-id", reported_run)])

    def test_should_close_a_reported_wave_once_its_integration_pull_request_is_merged(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("merged"), WAVE_REPORTED])
        runtime = self._create_runtime(TASK_DELIVERED, ForgeDouble(MERGED_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_last_event(),
            {
                "schema_version": 1,
                "ts": "2026-10-19T09:00:00Z",
                "event": "wave.closed",
                "wave": "tidepool_w16",
                "pr": 42,
            },
        )


WAVE_OF_TWO_TASKS_STARTED = {**WAVE_STARTED, "tasks": ["T7", "T8"]}
TASK_AFTER_T7 = (("MILESTONE", "@MILESTONE.M4"), ("STATUS", "todo"), ("AFTER", "@TASK.T7"))
GREEN_PULL_REQUEST = {**OPEN_PULL_REQUEST, "checks": [{"name": "ci", "verdict": "success"}]}
TASK_PASSED_AT_THE_HEAD = {
    "schema_version": 1,
    "ts": "2026-10-18T11:45:00Z",
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


LEDGER_OF_A_VERIFIED_TASK = [
    WAVE_OF_TWO_TASKS_STARTED,
    TASK_PR_OPENED,
    TASK_PREFLIGHTED_AT_THE_HEAD,
    TASK_PASSED_AT_THE_HEAD,
    _record_task_state("verified"),
]
OTHER_TASK_PASSED = {**TASK_PASSED_AT_THE_HEAD, "task": "T8", "pr": 43}
SAME_TASK_PASSED_IN_ANOTHER_WAVE = {**TASK_PASSED_AT_THE_HEAD, "wave": "tidepool_w15", "pr": 41}


class MergingForgeDouble:
    def __init__(self, found_by_branch: dict):
        self.found_by_branch = found_by_branch
        self.merges = []

    def find_pull_request(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "pull_request": self.found_by_branch.get(request["branch"])}

    def merge_pull_request(self, request: dict, runtime) -> dict:
        self.merges.append(request)
        return {"schema_version": 1}

    def describe_account(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "login": "tidepool-cli"}


class MergingForgeWithAnUnreadableAccountDouble(MergingForgeDouble):
    def describe_account(self, request: dict, runtime) -> dict:
        raise BrigadeError("gh api user failed")


class TickMergingAVerifiedTaskTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        self.repository = self.root / "tidepool"
        (self.repository / ".brigade" / "worktrees" / "T8").mkdir(parents=True)
        self.spawn = SpawnRecorderDouble()
        self.forge = MergingForgeDouble({"task/M4/T7": GREEN_PULL_REQUEST})
        write_ledger(self.root, LEDGER_OF_A_VERIFIED_TASK)
        self.runtime = self._create_runtime(self.forge)

    def _create_runtime(self, forge: MergingForgeDouble) -> Runtime:
        corpus = {
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"))},
            "TASK": {"T7": TASK_DELIVERED, "T8": TASK_AFTER_T7},
        }
        return create_runtime(
            self.root,
            run_process=create_machine_double(corpus, MACHINE_OUTPUTS),
            spawn_process=self.spawn.spawn,
            resolve_plugin=create_plugin_resolution(STEP_COUNTING_PROBE, forge),
        )

    def _read_events(self) -> list[dict]:
        lines = (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines]

    def test_should_merge_the_pull_request_by_the_method_of_the_project(self):
        # Act
        COMMAND.run(SimpleNamespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(
            self.forge.merges,
            [{"repository": str(self.repository), "number": 42, "method": "rebase", "environment": {}}],
        )

    def test_should_merge_nothing_when_the_login_the_merge_would_run_as_cannot_be_read(self):
        # Arrange
        forge = MergingForgeWithAnUnreadableAccountDouble({"task/M4/T7": GREEN_PULL_REQUEST})
        runtime = self._create_runtime(forge)

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), runtime)

        # Assert
        self.assertEqual(forge.merges, [])

    def test_should_record_the_merge_with_the_login_it_ran_as_and_the_task_merged(self):
        # Arrange
        first_event_of_the_tick = 5

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(
            self._read_events()[first_event_of_the_tick : first_event_of_the_tick + 2],
            [
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "pr.merged",
                    "project": "tidepool",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "pr": 42,
                    "rounds": 1,
                    "login": "tidepool-cli",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "merged",
                },
            ],
        )

    def test_should_count_as_review_rounds_the_verdicts_of_the_merged_task_in_its_wave_alone(self):
        # Arrange
        write_ledger(self.root, [*LEDGER_OF_A_VERIFIED_TASK, OTHER_TASK_PASSED, SAME_TASK_PASSED_IN_ANOTHER_WAVE])
        merged_event = 7

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(self._read_events()[merged_event]["rounds"], 1)

    def test_should_start_the_dependent_of_the_merged_task_in_the_same_tick(self):
        # Act
        COMMAND.run(SimpleNamespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(
            [argv[:3] for argv in self.spawn.argvs],
            [("run", "build-task", "task=@TASK.T8")],
        )


class OpeningForgeDouble:
    def __init__(self):
        self.opened = []

    def find_pull_request(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "pull_request": None}

    def open_pull_request(self, request: dict, runtime) -> dict:
        self.opened.append(request)
        return {"schema_version": 1, "url": "https://github.com/octo/tidepool/pull/77", "number": 77}

    def describe_account(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "login": "tidepool-cli"}


class TickOpeningTheIntegrationPullRequestTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        self.repository = self.root / "tidepool"
        self.forge = OpeningForgeDouble()
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("merged")])
        corpus = {
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"), ("FORGE", "github"))},
            "TASK": {"T7": TASK_DELIVERED},
        }
        self.runtime = create_runtime(
            self.root,
            run_process=create_machine_double(corpus, {**MACHINE_OUTPUTS, ("git", "ls-remote"): ""}),
            spawn_process=SpawnRecorderDouble().spawn,
            resolve_plugin=create_plugin_resolution(STEP_COUNTING_PROBE, self.forge),
        )

    def _read_last_event(self) -> dict:
        lines = (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8").splitlines()
        return json.loads(lines[-1])

    def test_should_open_the_pull_request_from_the_wave_branch_to_the_main_branch(self):
        # Act
        COMMAND.run(SimpleNamespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(
            self.forge.opened,
            [
                {
                    "repository": str(self.repository),
                    "base": "main",
                    "branch": "integration/M4",
                    "title": "chore(wave): merge the wave tidepool_w16 into main",
                    "body": "Integrates the wave tidepool_w16 of @PROJECT.tidepool into main: @TASK.T7.",
                    "milestone": None,
                    "environment": {},
                }
            ],
        )

    def test_should_record_the_opening_with_the_login_it_ran_as(self):
        # Act
        COMMAND.run(SimpleNamespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(
            self._read_last_event(),
            {
                "schema_version": 1,
                "ts": "2026-10-19T09:00:00Z",
                "event": "wave.pr_opened",
                "wave": "tidepool_w16",
                "pr": 77,
                "login": "tidepool-cli",
            },
        )

    def test_should_open_none_at_a_second_tick(self):
        # Arrange
        COMMAND.run(SimpleNamespace(mode="once"), self.runtime)

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(len(self.forge.opened), 1)


class TickStartingAndCuttingWavesTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        corpus = {
            "PROJECT": {"tidepool": (("PATH", str(self.root / "tidepool")), ("MAIN", "main"))},
            "TASK": {"T7": TASK_TO_DELIVER},
        }
        outputs = {
            **{prefix: ProcessAnswer(stdout=stdout) for prefix, stdout in MACHINE_OUTPUTS.items()},
            ("git", "branch", "--quiet"): ProcessAnswer(),
        }
        self.machine = ScriptedProcessRunner(outputs, fallback=create_corpus_double(corpus))
        self.runtime = create_runtime(
            self.root,
            run_process=self.machine.run,
            spawn_process=SpawnRecorderDouble().spawn,
            resolve_plugin=create_plugin_resolution(
                STEP_COUNTING_PROBE, ForgeDouble(NO_PULL_REQUEST, NO_DETAILS_ASKED)
            ),
        )

    def _miss_the_branch(self, branch: str) -> None:
        verify = ("git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}")
        self.machine.answers[verify] = ProcessAnswer(exit_code=1)

    def test_should_start_a_wave_of_the_candidates_of_a_project_without_one(self):
        # Arrange
        self._miss_the_branch("integration/tidepool_w1")

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), self.runtime)

        # Assert
        ledger = (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(
            json.loads(ledger[0]),
            {
                "schema_version": 2,
                "ts": ANY,
                "event": "wave.started",
                "wave": "tidepool_w1",
                "project": "tidepool",
                "branch": "integration/tidepool_w1",
                "tasks": ["T7"],
            },
        )
        self.assertIn(("git", "branch", "--quiet", "integration/tidepool_w1", "main"), self.machine.argvs)

    def test_should_cut_the_missing_branch_of_an_open_wave(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED])
        self._miss_the_branch("integration/M4")

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), self.runtime)

        # Assert
        self.assertIn(("git", "branch", "--quiet", "integration/M4", "main"), self.machine.argvs)


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


BEHIND_PULL_REQUEST = {**OPEN_PULL_REQUEST, "behind": True}
REBASED_HEAD = "9a9a9a9"
REBASED_PULL_REQUEST = {**OPEN_PULL_REQUEST, "head": REBASED_HEAD, "checks": [{"name": "ci", "verdict": "pending"}]}
REBASE_ONTO_THE_WAVE_BRANCH = ("git", "rebase", "origin/integration/M4")
FETCH_OF_THE_WAVE_BRANCH = ("git", "fetch", "--quiet", "origin", "integration/M4")
CLI_BOUND_TO_A_FORGE_ACCOUNT = '[forge_accounts]\ncli = "tidepool-cli"\n'
ENVIRONMENT_OF_THE_CLI_ACCOUNT = {"GH_TOKEN": "t0k3n"}
REBASE_OUTPUTS = {
    **{prefix: ProcessAnswer(stdout=stdout) for prefix, stdout in MACHINE_OUTPUTS.items()},
    REBASE_ONTO_THE_WAVE_BRANCH: ProcessAnswer(),
    ("git", "rebase", "--abort"): ProcessAnswer(),
    ("git", "rev-parse", "HEAD"): ProcessAnswer(stdout=f"{REBASED_HEAD}\n"),
    ("git", "push"): ProcessAnswer(),
}
CONFLICTING_REBASE = ProcessAnswer(exit_code=1, stderr="CONFLICT (content): Merge conflict in src/tides.py")
OUTPUTS_OF_A_REBASE_STOPPED_ON_A_CONFLICT = {
    **REBASE_OUTPUTS,
    REBASE_ONTO_THE_WAVE_BRANCH: CONFLICTING_REBASE,
    ("git", "rev-parse", "--quiet", "--verify", "REBASE_HEAD"): ProcessAnswer(stdout="f02da32\n"),
}
LEDGER_OF_A_TASK_IN_VERIFYING = [
    WAVE_STARTED,
    TASK_PR_OPENED,
    TASK_PREFLIGHTED_AT_THE_HEAD,
    _record_task_state("verifying"),
]
LEDGER_OF_A_TASK_PAST_ITS_ROUNDS = [
    *LEDGER_OF_A_TASK_IN_VERIFYING,
    _record_task_state("fixing"),
    _record_task_state("fixing"),
    _record_task_state("verifying"),
]


class RebasingForgeDouble:
    def __init__(self, found: list[dict]):
        self.found = found

    def find_pull_request(self, request: dict, runtime) -> dict:
        pull_request = self.found[0] if len(self.found) == 1 else self.found.pop(0)
        return {"schema_version": 1, "pull_request": pull_request}

    def describe_account(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "login": "tidepool-cli"}

    def read_login_environment(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "environment": ENVIRONMENT_OF_THE_CLI_ACCOUNT}


class TickRebasingATaskBehindTheWaveBranchTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        self.repository = self.root / "tidepool"
        self.worktree = self.repository / ".brigade" / "worktrees" / "T7"
        self.worktree.mkdir(parents=True)
        self.spawn = SpawnRecorderDouble()
        self.lock_free_at_the_rebase = []
        self.environments_of_the_fetch = []

    def _create_runtime(self, outputs: dict, found: list[dict]) -> Runtime:
        corpus = {
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"))},
            "TASK": {"T7": TASK_DELIVERED},
        }
        self.machine = ScriptedProcessRunner(outputs, fallback=create_corpus_double(corpus))
        forge = RebasingForgeDouble(found)
        return create_runtime(
            self.root,
            run_process=self._observe_the_lock(self.machine.run),
            spawn_process=self.spawn.spawn,
            resolve_plugin=create_plugin_resolution(STEP_COUNTING_PROBE, forge),
        )

    def _observe_the_lock(self, run_process):
        def run(request):
            if request.argv == FETCH_OF_THE_WAVE_BRANCH:
                self.environments_of_the_fetch.append(request.environment)
            if request.argv == REBASE_ONTO_THE_WAVE_BRANCH:
                lock = self.root / "state" / "locks" / "worktrees-tidepool.lock"
                with contextlib.ExitStack() as stack:
                    lock.parent.mkdir(parents=True, exist_ok=True)
                    lock_file = stack.enter_context(lock.open("a", encoding="utf-8"))
                    try:
                        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        self.lock_free_at_the_rebase.append(True)
                    except BlockingIOError:
                        self.lock_free_at_the_rebase.append(False)
            return run_process(request)

        return run

    def _read_events(self) -> list[dict]:
        lines = (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines]

    def test_should_rebase_the_task_branch_in_its_worktree_and_push_it_with_a_lease_on_its_head(self):
        # Arrange
        write_ledger(self.root, LEDGER_OF_A_TASK_IN_VERIFYING)
        runtime = self._create_runtime(REBASE_OUTPUTS, [BEHIND_PULL_REQUEST, REBASED_PULL_REQUEST])

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            [argv for argv in self.machine.argvs if argv[:2] in {("git", "rebase"), ("git", "push")}],
            [
                REBASE_ONTO_THE_WAVE_BRANCH,
                ("git", "push", "--quiet", "--force-with-lease=task/M4/T7:8885daa", "origin", "HEAD:task/M4/T7"),
            ],
        )

    def test_should_record_the_rebase_with_both_heads_and_the_login_of_the_push_and_send_the_task_to_its_preflight(
        self,
    ):
        # Arrange
        write_ledger(self.root, LEDGER_OF_A_TASK_IN_VERIFYING)
        runtime = self._create_runtime(REBASE_OUTPUTS, [BEHIND_PULL_REQUEST, REBASED_PULL_REQUEST])

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_events()[4:],
            [
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.rebased",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "before": "8885daa",
                    "after": REBASED_HEAD,
                    "login": "tidepool-cli",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "pr_open",
                },
            ],
        )

    def test_should_rebase_under_the_lock_of_the_worktrees_of_the_project(self):
        # Arrange
        write_ledger(self.root, LEDGER_OF_A_TASK_IN_VERIFYING)
        runtime = self._create_runtime(REBASE_OUTPUTS, [BEHIND_PULL_REQUEST, REBASED_PULL_REQUEST])

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), runtime)

        # Assert
        self.assertEqual(self.lock_free_at_the_rebase, [False])

    def test_should_fetch_the_wave_branch_as_the_forge_account_of_the_cli(self):
        # Arrange
        (self.root / "config" / "config.toml").write_text(
            CLIENT_AND_DOCUMENT_CONFIGURATION + CLI_BOUND_TO_A_FORGE_ACCOUNT, encoding="utf-8"
        )
        write_ledger(self.root, LEDGER_OF_A_TASK_IN_VERIFYING)
        runtime = self._create_runtime(REBASE_OUTPUTS, [BEHIND_PULL_REQUEST, REBASED_PULL_REQUEST])

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), runtime)

        # Assert
        self.assertEqual(self.environments_of_the_fetch, [ENVIRONMENT_OF_THE_CLI_ACCOUNT])

    def test_should_abort_a_conflicting_rebase_and_launch_the_rebase_slot_in_fixing(self):
        # Arrange
        write_ledger(self.root, LEDGER_OF_A_TASK_IN_VERIFYING)
        runtime = self._create_runtime(OUTPUTS_OF_A_REBASE_STOPPED_ON_A_CONFLICT, [BEHIND_PULL_REQUEST])

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            (
                [argv for argv in self.machine.argvs if argv[:2] in {("git", "rebase"), ("git", "push")}],
                self.spawn.argvs,
                self._read_events()[4:],
            ),
            (
                [REBASE_ONTO_THE_WAVE_BRANCH, ("git", "rebase", "--abort")],
                [
                    (
                        "run",
                        "rebase-on-base",
                        "pr=42",
                        "task=@TASK.T7",
                        "--slot",
                        "rebase",
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
                [
                    {
                        "schema_version": 1,
                        "ts": "2026-10-19T09:00:00Z",
                        "event": "task.state",
                        "wave": "tidepool_w16",
                        "task": "T7",
                        "state": "fixing",
                    }
                ],
            ),
        )

    def test_should_park_on_a_conflict_a_task_whose_repair_rounds_are_spent(self):
        # Arrange
        write_ledger(self.root, LEDGER_OF_A_TASK_PAST_ITS_ROUNDS)
        runtime = self._create_runtime(OUTPUTS_OF_A_REBASE_STOPPED_ON_A_CONFLICT, [BEHIND_PULL_REQUEST])

        # Act
        COMMAND.run(SimpleNamespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            (self.spawn.argvs, self._read_events()[7:8]),
            (
                [("study", "run", "wave-report", "--run-id", ANY)],
                [
                    {
                        "schema_version": 1,
                        "ts": "2026-10-19T09:00:00Z",
                        "event": "task.parked",
                        "wave": "tidepool_w16",
                        "task": "T7",
                        "reason": "past 2 repair rounds",
                        "blockers": [],
                    }
                ],
            ),
        )
