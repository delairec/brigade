import contextlib
import dataclasses
import fcntl
import io
import json
import os
import signal
import tempfile
import unittest
from argparse import Namespace
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import ANY

from brigade.collectors import pr_threads
from brigade.commands.tick import COMMAND
from brigade.errors import BrigadeError, CommandFailed, StandingDown, UsageError
from brigade.runtime import Runtime
from brigade.system.collector_places import locate_collectors
from brigade.system.resolve_collector import BuiltInCollector, resolve_collector
from tests.unit.commands.command_runtime import (
    ProcessAnswer,
    ScriptedProcessRunner,
    create_corpus_double,
    create_machine_double,
    write_ledger,
    write_operational_corpus,
)
from tests.unit.commands.create_plugin_resolver import create_plugin_resolver
from tests.unit.commands.run_directories import FIRST_RUN, create_run_record, create_run_result, write_run
from tests.unit.commands.run_doubles import (
    CLIENT_AND_DOCUMENT_CONFIGURATION,
    STEP_COUNTING_PROBE,
    create_plugin_resolution,
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.forge_double import ForgeDouble
from tests.unit.plugin_double import PluginDouble
from tests.unit.select_argvs_opening_on import select_argvs_opening_on
from tests.unit.select_milestone_events import select_milestone_events
from tests.unit.select_wave_events import select_wave_events
from tests.unit.spawned_process_double import SpawnedProcessDouble

GIT_PUSH = ("git", "push")
GIT_REBASE = ("git", "rebase")

LOOP_MODE = "loop"
WAKE_THE_LOOP = signal.SIGUSR1


def _ignore_signal(_received, _frame) -> None:
    pass


def _create_runtime(root: Path, now: datetime) -> Runtime:
    return create_test_runtime(create_test_paths(root), now=now)


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
        request = Namespace(
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
                request = Namespace(mode=mode, create_runtime=_stop_the_loop_it_entered)

                # Act
                with self.assertRaises(UsageError) as raised, contextlib.redirect_stderr(io.StringIO()):
                    COMMAND.run(request, runtime)

                # Assert
                self.assertEqual(str(raised.exception), expected_message)


def _resolve_a_forge(kind: str, name: str, **places):
    return PluginDouble(kind=kind, name=name)


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
        request = Namespace(mode="once")

        runtime = dataclasses.replace(_create_quiet_runtime(self.root), read_monotonic=iter([100.0, 100.25]).__next__)

        # Act
        document = COMMAND.run(request, runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "mode": "once",
                "ts": "2026-10-07T09:00:00Z",
                "duration_ms": 250,
                "actions_applied": 0,
                "actions_failed": 0,
                "heartbeat": str(self.root / "state" / "tick.json"),
            },
        )
        self.assertEqual(
            json.loads((self.root / "state" / "tick.json").read_text(encoding="utf-8")),
            {
                "schema_version": 1,
                "ts": "2026-10-07T09:00:00Z",
                "duration_ms": 250,
                "actions_applied": 0,
                "actions_failed": 0,
            },
        )

    def test_should_stand_down_while_another_tick_holds_the_lock(self):
        # Arrange
        request = Namespace(mode="once")
        self.lock.parent.mkdir(parents=True)

        # Act
        with self.lock.open("a") as held, self.assertRaises(StandingDown) as raised:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            COMMAND.run(request, _create_quiet_runtime(self.root))

        # Assert
        self.assertEqual(str(raised.exception), f"another tick holds {self.lock}")

    def test_should_plan_nothing_on_a_dry_run(self):
        # Arrange
        request = Namespace(mode="dry-run")

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
                    "milestones": [],
                },
                "plan": [],
            },
        )

    def test_should_write_no_tick_trail_on_a_dry_run(self):
        # Arrange
        request = Namespace(mode="dry-run")

        # Act
        COMMAND.run(request, _create_quiet_runtime(self.root))

        # Assert
        self.assertEqual((self.root / "state" / "ticks").exists(), False)

    def test_should_report_each_round_of_the_loop_on_stderr(self):
        # Arrange
        create_round = _create_single_round_factory(
            dataclasses.replace(_create_quiet_runtime(self.root), read_monotonic=iter([100.0, 100.25]).__next__)
        )
        request = Namespace(mode=LOOP_MODE, create_runtime=create_round)
        reported = io.StringIO()

        # Act
        with contextlib.redirect_stderr(reported):
            document = COMMAND.run(request, _create_quiet_runtime(self.root))

        # Assert
        self.assertEqual(document, {"schema_version": 1, "mode": "loop", "ticks_attempted": 1})
        self.assertEqual(
            reported.getvalue(), "brigade tick: 2026-10-07T09:00:00Z: 0 actions applied, 0 failed in 250 ms\n"
        )

    def test_should_report_a_round_of_the_loop_another_tick_holds(self):
        # Arrange
        create_round = _create_single_round_factory(
            dataclasses.replace(_create_quiet_runtime(self.root), read_monotonic=iter([100.0, 100.25]).__next__)
        )
        request = Namespace(mode=LOOP_MODE, create_runtime=create_round)
        self.lock.parent.mkdir(parents=True)
        reported = io.StringIO()

        # Act
        with self.lock.open("a") as held, contextlib.redirect_stderr(reported):
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            COMMAND.run(request, _create_quiet_runtime(self.root))

        # Assert
        self.assertEqual(reported.getvalue(), f"brigade tick: another tick holds {self.lock}\n")

    def test_should_leave_the_lock_the_heartbeat_and_the_trail_alone_in_the_state_directory(self):
        # Arrange
        request = Namespace(mode="once")
        state = self.root / "state"

        # Act
        COMMAND.run(request, _create_quiet_runtime(self.root))

        # Assert
        self.assertCountEqual(state.iterdir(), [state / "locks", state / "tick.json", state / "ticks"])
        self.assertCountEqual((state / "locks").iterdir(), [self.lock])
        self.assertCountEqual((state / "ticks").iterdir(), [state / "ticks" / "20261007T090000Z.jsonl"])

    def test_should_write_nothing_but_the_lock_while_another_tick_holds_it(self):
        # Arrange
        request = Namespace(mode="once")
        self.lock.parent.mkdir(parents=True)

        # Act
        with self.lock.open("a") as held, contextlib.suppress(StandingDown):
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            COMMAND.run(request, _create_quiet_runtime(self.root))

        # Assert
        self.assertCountEqual((self.root / "state").iterdir(), [self.root / "state" / "locks"])

    def test_should_write_no_heartbeat_when_the_trail_directory_cannot_be_created(self):
        # Arrange
        request = Namespace(mode="once")
        trails = self.root / "state" / "ticks"
        trails.parent.mkdir()
        trails.write_text("", encoding="utf-8")

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(request, _create_quiet_runtime(self.root))

        # Assert
        self.assertEqual(str(raised.exception), f"cannot write {trails}: File exists")
        self.assertEqual((self.root / "state" / "tick.json").exists(), False)

    def test_should_take_no_lock_and_write_no_heartbeat_on_a_dry_run(self):
        # Arrange
        request = Namespace(mode="dry-run")

        # Act
        COMMAND.run(request, _create_quiet_runtime(self.root))

        # Assert
        self.assertEqual((self.root / "state" / "locks").exists(), False)
        self.assertEqual((self.root / "state" / "tick.json").exists(), False)

    def test_should_plan_while_another_tick_holds_the_lock(self):
        # Arrange
        request = Namespace(mode="dry-run")
        self.lock.parent.mkdir(parents=True)

        # Act
        with self.lock.open("a") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            document = COMMAND.run(request, _create_quiet_runtime(self.root))

        # Assert
        self.assertEqual(document["plan"], [])

    def test_should_count_a_round_of_the_loop_another_tick_holds_and_write_no_heartbeat(self):
        # Arrange
        create_round = _create_single_round_factory(_create_quiet_runtime(self.root))
        request = Namespace(mode=LOOP_MODE, create_runtime=create_round)
        self.lock.parent.mkdir(parents=True)

        # Act
        with self.lock.open("a") as held, contextlib.redirect_stderr(io.StringIO()):
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            document = COMMAND.run(request, _create_quiet_runtime(self.root))

        # Assert
        self.assertEqual(document, {"schema_version": 1, "mode": "loop", "ticks_attempted": 1})
        self.assertEqual((self.root / "state" / "tick.json").exists(), False)

    def test_should_report_a_failed_round_of_the_loop_and_count_it(self):
        # Arrange
        (self.root / "state").write_text("", encoding="utf-8")
        create_round = _create_single_round_factory(_create_quiet_runtime(self.root))
        request = Namespace(mode=LOOP_MODE, create_runtime=create_round)
        reported = io.StringIO()

        # Act
        with contextlib.redirect_stderr(reported):
            document = COMMAND.run(request, _create_quiet_runtime(self.root))

        # Assert
        self.assertEqual(document, {"schema_version": 1, "mode": "loop", "ticks_attempted": 1})
        self.assertEqual(
            reported.getvalue(), f"brigade tick: cannot write {self.root / 'state' / 'locks'}: Not a directory\n"
        )


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
                "a dry run of an empty machine",
                {
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
                        "milestones": [],
                    },
                    "plan": [],
                },
                (
                    "snapshot\n  now  2026-10-07T09:00:00Z\n  waves  []\n  projects  []\n  studies  []"
                    "\n  live_study_runs  []\n  study_runs  2\n  rate_limits  []"
                    "\n  milestones  []\nplan\n  no action"
                ),
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
        options = Namespace(mode="once")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


WAVE = "tidepool_w16"
WAVE_BRANCH = "integration/M4"
WAVE_HEAD = "8885daa"
MAIN_HEAD = "4c1d2e0"
TASK_TO_DELIVER = (("MILESTONE", "@MILESTONE.M4"), ("STATUS", "todo"))
TASK_DELIVERED = (("MILESTONE", "@MILESTONE.M4"), ("STATUS", "implemented"), ("DELIVERED_BY", "42"))
MILESTONE_M4 = (("STATUS", "active"), ("TITLE", "Tides"))
CUT_OF_M4 = {
    "schema_version": 1,
    "ts": "2026-10-18T09:30:00Z",
    "event": "milestone.branch_cut",
    "project": "tidepool",
    "milestone": "M4",
    "branch": "integration/tides",
    "login": "tidepool-cli",
}
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
    ("git", "add"): "",
    ("awawa", "diff"): '{"added": [], "changed": [], "removed": []}',
}
MACHINE_ANSWERS = {prefix: ProcessAnswer(stdout=stdout) for prefix, stdout in MACHINE_OUTPUTS.items()}
WAVE_TREE_HOLDING_T7_IMPLEMENTED_OUTPUTS = {
    ("awawa", "status", "TASK", "--where", "STATUS==implemented"): '{"entities": [{"type": "TASK", "name": "T7"}]}',
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
PAUSED_ON_THE_QUOTA_UNTIL_08 = {
    "schema_version": 1,
    "ts": "2026-10-19T07:30:00Z",
    "event": "wave.paused",
    "wave": "tidepool_w16",
    "reason": "quota",
    "resume_at": "2026-10-19T08:00:00Z",
}
FORGE_ACCOUNT_UNAVAILABLE = {
    "schema_version": 1,
    "ts": "2026-10-19T08:00:00Z",
    "event": "forge_account.unavailable",
    "login": "octo-bot",
    "key": "build",
}
PAUSED_ON_THE_FORGE_ACCOUNT = {
    "schema_version": 1,
    "ts": "2026-10-19T08:10:00Z",
    "event": "wave.paused",
    "wave": "tidepool_w16",
    "reason": "forge_account",
    "resume_at": None,
}
RESUMED_FROM_THE_FORGE_ACCOUNT = {
    "schema_version": 1,
    "ts": "2026-10-19T08:20:00Z",
    "event": "wave.resumed",
    "wave": "tidepool_w16",
    "reason": "forge_account",
}
PAUSED_TRIAGE = (
    ("SLOT", "triage"),
    ("OUTPUT", "entity:PATTERN"),
    ("ANSWER", "PATTERN"),
    ("STATUS", "paused"),
)
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


class CheckLogsReaderDouble:
    def __init__(self, tails: dict | None):
        self.tails = tails

    def read_check_logs(self, request: dict) -> dict:
        return {"schema_version": 1, "logs": [{"name": name, "tail": self.tails[name]} for name in request["checks"]]}


def create_forge(found: dict | None, details: dict | None, tails: dict | None = None) -> ForgeDouble:
    return ForgeDouble(
        {
            "find_pull_request": lambda request: {"schema_version": 1, "pull_request": found},
            "read_pull_request": lambda request: {"schema_version": 1, "pull_request": details},
            "read_check_logs": CheckLogsReaderDouble(tails).read_check_logs,
        }
    )


class SpawnReadingTheLedgerDouble:
    def __init__(self, ledger: Path):
        self.ledger = ledger
        self.last_events_at_spawn = []

    def spawn(self, request):
        self.last_events_at_spawn.append(json.loads(self.ledger.read_text(encoding="utf-8").splitlines()[-1]))
        return SpawnedProcessDouble(pid=os.getpid())


class SpawnRecorderDouble:
    def __init__(self):
        self.argvs = []

    def spawn(self, request):
        self.argvs.append(request.argv[2:])
        return SpawnedProcessDouble(pid=os.getpid())


class TickApplyingTheActionsOfAWaveTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        self.repository = self.root / "tidepool"
        self.worktree = self.repository / ".brigade" / "worktrees" / "T7"
        self.spawn = SpawnRecorderDouble()

    def _create_runtime(self, task: tuple, forge: ForgeDouble, setup: tuple = (), requests: tuple = ()) -> Runtime:
        corpus = {
            "STUDY": {"triage": PAUSED_TRIAGE},
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"), *setup)},
            "TASK": {"T7": task},
            "REQUEST": dict(requests),
        }
        return create_test_runtime(
            create_test_paths(self.root),
            run_process=create_machine_double(corpus, MACHINE_OUTPUTS),
            spawn_process=self.spawn.spawn,
            resolve_plugin=create_plugin_resolution(STEP_COUNTING_PROBE, forge),
        )

    def _read_events(self) -> list[dict]:
        return list(
            map(json.loads, (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8").splitlines())
        )

    def test_should_launch_the_build_run_of_a_task_ready_to_start(self):
        # Arrange
        self.worktree.mkdir(parents=True)
        write_ledger(self.root, [WAVE_STARTED])
        runtime = self._create_runtime(TASK_TO_DELIVER, create_forge(NO_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        document = COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(document["actions_applied"], 1)
        self.assertEqual(
            self.spawn.argvs,
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
        )

    def test_should_record_the_task_running_before_its_build_run_is_spawned(self):
        # Arrange
        self.worktree.mkdir(parents=True)
        write_ledger(self.root, [WAVE_STARTED])
        self.spawn = SpawnReadingTheLedgerDouble(self.root / "state" / "ledger" / "2026-10.jsonl")
        runtime = self._create_runtime(TASK_TO_DELIVER, create_forge(NO_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

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
        runtime = self._create_runtime(TASK_TO_DELIVER, create_forge(NO_PULL_REQUEST, NO_DETAILS_ASKED), broken_setup)

        # Act
        document = COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(document["actions_failed"], 1)
        self.assertEqual(
            json.loads((self.root / "state" / "tick.json").read_text(encoding="utf-8"))["actions_failed"], 1
        )
        self.assertEqual(
            self._read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-18T09:00:00Z",
                    "event": "wave.started",
                    "wave": "tidepool_w16",
                    "project": "tidepool",
                    "branch": "integration/M4",
                    "tasks": ["T7"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "parked",
                    "reason": "setup failed",
                },
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
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "order.started",
                    "project": "tidepool",
                    "kind": "study",
                    "order": "wave-report",
                    "run": ANY,
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "wave.reported",
                    "wave": "tidepool_w16",
                    "run": ANY,
                },
            ],
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
        runtime = self._create_runtime(TASK_TO_DELIVER, create_forge(NO_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

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
        runtime = self._create_runtime(TASK_TO_DELIVER, create_forge(NO_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

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
        runtime = self._create_runtime(TASK_DELIVERED, create_forge(MERGED_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-18T09:00:00Z",
                    "event": "wave.started",
                    "wave": "tidepool_w16",
                    "project": "tidepool",
                    "branch": "integration/M4",
                    "tasks": ["T7"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "running",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "merged",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "order.started",
                    "project": "tidepool",
                    "kind": "study",
                    "order": "wave-report",
                    "run": ANY,
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "wave.reported",
                    "wave": "tidepool_w16",
                    "run": ANY,
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "wave.closed",
                    "wave": "tidepool_w16",
                    "pr": 42,
                },
            ],
        )

    def test_should_record_the_merge_of_the_pull_request_of_a_queued_task_the_wave_tree_holds_implemented(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("queued")])
        corpus = {
            "STUDY": {"triage": PAUSED_TRIAGE},
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"))},
            "TASK": {"T7": TASK_DELIVERED},
        }
        runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=create_machine_double(corpus, {**MACHINE_OUTPUTS, **WAVE_TREE_HOLDING_T7_IMPLEMENTED_OUTPUTS}),
            spawn_process=self.spawn.spawn,
            resolve_plugin=create_plugin_resolution(
                STEP_COUNTING_PROBE, create_forge(MERGED_PULL_REQUEST, NO_DETAILS_ASKED)
            ),
        )

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-18T09:00:00Z",
                    "event": "wave.started",
                    "wave": "tidepool_w16",
                    "project": "tidepool",
                    "branch": "integration/M4",
                    "tasks": ["T7"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "queued",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "merged",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "order.started",
                    "project": "tidepool",
                    "kind": "study",
                    "order": "wave-report",
                    "run": ANY,
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "wave.reported",
                    "wave": "tidepool_w16",
                    "run": ANY,
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "wave.closed",
                    "wave": "tidepool_w16",
                    "pr": 42,
                },
            ],
        )

    def test_should_hold_for_verification_a_pull_request_passing_its_preflight(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("pr_open"), TASK_PR_OPENED])
        runtime = self._create_runtime(TASK_DELIVERED, create_forge(OPEN_PULL_REQUEST, PULL_REQUEST_DETAILS))

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-18T09:00:00Z",
                    "event": "wave.started",
                    "wave": "tidepool_w16",
                    "project": "tidepool",
                    "branch": "integration/M4",
                    "tasks": ["T7"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "pr_open",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T11:00:00Z",
                    "event": "task.pr_opened",
                    "project": "tidepool",
                    "task": "T7",
                    "wave": "tidepool_w16",
                    "branch": "task/M4/T7",
                    "pr": 42,
                    "login": "tidepool-bot",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.preflighted",
                    "project": "tidepool",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "pr": 42,
                    "head": "8885daa",
                    "checks": [
                        {
                            "name": "ancestry",
                            "verdict": "pass",
                            "findings": [],
                        },
                        {
                            "name": "checks",
                            "verdict": "pass",
                            "findings": [],
                        },
                        {
                            "name": "corpus",
                            "verdict": "pass",
                            "findings": [],
                        },
                        {
                            "name": "promotion",
                            "verdict": "pass",
                            "findings": [],
                        },
                        {
                            "name": "untouched_files",
                            "verdict": "pass",
                            "findings": [],
                        },
                        {
                            "name": "privacy",
                            "verdict": "pass",
                            "findings": [],
                        },
                        {
                            "name": "body",
                            "verdict": "pass",
                            "findings": [],
                        },
                        {
                            "name": "size",
                            "verdict": "info",
                            "findings": ["0 files", "0 lines", "0 packages", "0 layers"],
                        },
                    ],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "verifying",
                },
            ],
        )

    def test_should_record_the_findings_of_the_preflight_in_the_ledger(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("pr_open"), TASK_PR_OPENED])
        runtime = self._create_runtime(TASK_DELIVERED, create_forge(OPEN_PULL_REQUEST, PULL_REQUEST_DETAILS))

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-18T09:00:00Z",
                    "event": "wave.started",
                    "wave": "tidepool_w16",
                    "project": "tidepool",
                    "branch": "integration/M4",
                    "tasks": ["T7"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "pr_open",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T11:00:00Z",
                    "event": "task.pr_opened",
                    "project": "tidepool",
                    "task": "T7",
                    "wave": "tidepool_w16",
                    "branch": "task/M4/T7",
                    "pr": 42,
                    "login": "tidepool-bot",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.preflighted",
                    "project": "tidepool",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "pr": 42,
                    "head": "8885daa",
                    "checks": [
                        {
                            "name": "ancestry",
                            "verdict": "pass",
                            "findings": [],
                        },
                        {
                            "name": "checks",
                            "verdict": "pass",
                            "findings": [],
                        },
                        {
                            "name": "corpus",
                            "verdict": "pass",
                            "findings": [],
                        },
                        {
                            "name": "promotion",
                            "verdict": "pass",
                            "findings": [],
                        },
                        {
                            "name": "untouched_files",
                            "verdict": "pass",
                            "findings": [],
                        },
                        {
                            "name": "privacy",
                            "verdict": "pass",
                            "findings": [],
                        },
                        {
                            "name": "body",
                            "verdict": "pass",
                            "findings": [],
                        },
                        {
                            "name": "size",
                            "verdict": "info",
                            "findings": ["0 files", "0 lines", "0 packages", "0 layers"],
                        },
                    ],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "verifying",
                },
            ],
        )

    def test_should_launch_the_procedure_the_key_build_of_procedures_names_in_place_of_build_task(self):
        # Arrange
        deliver = self.root / "deliver.md"
        deliver.write_text("---\ncapabilities: read\nbudget: 40\n---\nDeliver the task.\n", encoding="utf-8")
        (self.root / "config" / "config.toml").write_text(
            f'{CLIENT_AND_DOCUMENT_CONFIGURATION}[procedures]\nbuild = "{deliver}"\n', encoding="utf-8"
        )
        self.worktree.mkdir(parents=True)
        write_ledger(self.root, [WAVE_STARTED])
        runtime = self._create_runtime(TASK_TO_DELIVER, create_forge(NO_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self.spawn.argvs,
            [
                (
                    "run",
                    f"{self.root}/deliver.md",
                    "task=@TASK.T7",
                    "base=integration/M4",
                    "--slot",
                    "build",
                    "--cwd",
                    f"{self.root}/tidepool/.brigade/worktrees/T7",
                    "--project",
                    "tidepool",
                    "--brief",
                    f"{self.root}/state/briefs/tidepool_w16-T7.md",
                    "--wave",
                    "tidepool_w16",
                    "--task",
                    "T7",
                    "--run-id",
                    ANY,
                )
            ],
        )

    def test_should_launch_the_verification_of_a_task_in_verifying(self):
        # Arrange
        self.worktree.mkdir(parents=True)
        write_ledger(
            self.root, [WAVE_STARTED, TASK_PR_OPENED, TASK_PREFLIGHTED_AT_THE_HEAD, _record_task_state("verifying")]
        )
        runtime = self._create_runtime(TASK_DELIVERED, create_forge(OPEN_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

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
        runtime = self._create_runtime(TASK_DELIVERED, create_forge(OPEN_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self.spawn.argvs,
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
        )
        self.assertEqual(
            self._read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-18T09:00:00Z",
                    "event": "wave.started",
                    "wave": "tidepool_w16",
                    "project": "tidepool",
                    "branch": "integration/M4",
                    "tasks": ["T7"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T11:00:00Z",
                    "event": "task.pr_opened",
                    "project": "tidepool",
                    "task": "T7",
                    "wave": "tidepool_w16",
                    "branch": "task/M4/T7",
                    "pr": 42,
                    "login": "tidepool-bot",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T11:30:00Z",
                    "event": "task.preflighted",
                    "project": "tidepool",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "pr": 42,
                    "head": "8885daa",
                    "checks": [],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "changes_requested",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "fixing",
                },
            ],
        )

    def test_should_ask_the_forge_for_the_last_200_lines_of_the_log_of_each_failing_check(self):
        # Arrange
        self.worktree.mkdir(parents=True)
        write_ledger(
            self.root,
            [WAVE_STARTED, TASK_PR_OPENED, TASK_PREFLIGHTED_ON_FAILING_CHECKS, _record_task_state("pr_open")],
        )
        forge = create_forge(PULL_REQUEST_FAILING_TWO_CHECKS, NO_DETAILS_ASKED, {"ci": None, "coverage": None})
        runtime = self._create_runtime(TASK_DELIVERED, forge)

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            forge.list_requests("read_check_logs"),
            [
                {
                    "schema_version": 1,
                    "repository": f"{self.root}/tidepool",
                    "number": 42,
                    "checks": ["ci", "coverage"],
                    "lines": 200,
                    "environment": {},
                }
            ],
        )

    def test_should_launch_the_repair_of_the_failing_checks_with_the_tail_of_their_logs_and_record_it_in_fixing(self):
        # Arrange
        self.worktree.mkdir(parents=True)
        write_ledger(
            self.root,
            [WAVE_STARTED, TASK_PR_OPENED, TASK_PREFLIGHTED_ON_FAILING_CHECKS, _record_task_state("pr_open")],
        )
        tails = {"ci": "FAIL test_cart\nexit 1", "coverage": None}
        runtime = self._create_runtime(
            TASK_DELIVERED, create_forge(PULL_REQUEST_FAILING_TWO_CHECKS, NO_DETAILS_ASKED, tails)
        )

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        brief = self.root / "state" / "briefs" / "tidepool_w16-T7-checks.md"
        self.assertEqual(
            self.spawn.argvs,
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
        )
        self.assertEqual(
            brief.read_text(),
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
            "The forge keeps no log of this check.\n",
        )
        self.assertEqual(
            self._read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-18T09:00:00Z",
                    "event": "wave.started",
                    "wave": "tidepool_w16",
                    "project": "tidepool",
                    "branch": "integration/M4",
                    "tasks": ["T7"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T11:00:00Z",
                    "event": "task.pr_opened",
                    "project": "tidepool",
                    "task": "T7",
                    "wave": "tidepool_w16",
                    "branch": "task/M4/T7",
                    "pr": 42,
                    "login": "tidepool-bot",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T11:30:00Z",
                    "event": "task.preflighted",
                    "project": "tidepool",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "pr": 42,
                    "head": "8885daa",
                    "checks": [
                        {
                            "name": "checks",
                            "verdict": "fail",
                            "findings": ["ci: failure", "coverage: failure"],
                        },
                    ],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "pr_open",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "fixing",
                },
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
        runtime = self._create_runtime(TASK_DELIVERED, create_forge(OPEN_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-18T09:00:00Z",
                    "event": "wave.started",
                    "wave": "tidepool_w16",
                    "project": "tidepool",
                    "branch": "integration/M4",
                    "tasks": ["T7"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T11:00:00Z",
                    "event": "task.pr_opened",
                    "project": "tidepool",
                    "task": "T7",
                    "wave": "tidepool_w16",
                    "branch": "task/M4/T7",
                    "pr": 42,
                    "login": "tidepool-bot",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T11:30:00Z",
                    "event": "task.preflighted",
                    "project": "tidepool",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "pr": 42,
                    "head": "8885daa",
                    "checks": [],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "verifying",
                },
                {
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
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "verified",
                },
            ],
        )

    def test_should_park_a_queued_task_a_live_blocker_cites(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("queued")])
        corpus = {
            "STUDY": {"triage": PAUSED_TRIAGE},
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"))},
            "TASK": {"T7": TASK_TO_DELIVER},
        }
        runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=create_machine_double(corpus, {**MACHINE_OUTPUTS, **BLOCKING_QUESTION_OUTPUTS}),
            spawn_process=self.spawn.spawn,
            resolve_plugin=create_plugin_resolution(
                STEP_COUNTING_PROBE, create_forge(NO_PULL_REQUEST, NO_DETAILS_ASKED)
            ),
        )

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-18T09:00:00Z",
                    "event": "wave.started",
                    "wave": "tidepool_w16",
                    "project": "tidepool",
                    "branch": "integration/M4",
                    "tasks": ["T7"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "queued",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.parked",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "reason": "blocked",
                    "blockers": ["OPEN_QUESTION.Undecided"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "order.started",
                    "project": "tidepool",
                    "kind": "study",
                    "order": "wave-report",
                    "run": ANY,
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "wave.reported",
                    "wave": "tidepool_w16",
                    "run": ANY,
                },
            ],
        )

    def test_should_pause_the_wave_of_a_task_whose_run_hit_the_quota(self):
        # Arrange
        rate_limited = {
            **create_run_result(FIRST_RUN, "failed", "2026-10-19T08:50:00Z"),
            "wave": WAVE,
            "task": "T7",
            "error_class": "rate_limit",
        }
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("running"), rate_limited])
        runtime = self._create_runtime(TASK_TO_DELIVER, create_forge(NO_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-18T09:00:00Z",
                    "event": "wave.started",
                    "wave": "tidepool_w16",
                    "project": "tidepool",
                    "branch": "integration/M4",
                    "tasks": ["T7"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "running",
                },
                {
                    "schema_version": 2,
                    "ts": "2026-10-19T08:50:00Z",
                    "event": "run.finished",
                    "run": ANY,
                    "segment": 1,
                    "procedure": "deliver",
                    "slot": "build",
                    "role": "builder",
                    "client": "fake",
                    "project": None,
                    "session": "session-b74",
                    "main_steps": 12,
                    "total_steps": 12,
                    "duration_ms": 4200,
                    "usage": None,
                    "outcome": "failed",
                    "error_class": "rate_limit",
                    "exit": 0,
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "nulls": {},
                    "message": "the task is delivered",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "wave.paused",
                    "wave": "tidepool_w16",
                    "reason": "quota",
                    "resume_at": "2026-10-19T09:30:00Z",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "paused:quota",
                },
            ],
        )

    def test_should_pause_the_wave_until_the_hour_the_quota_resets(self):
        # Arrange
        rate_limited = {
            **create_run_result(FIRST_RUN, "failed", "2026-10-19T08:50:00Z"),
            "wave": WAVE,
            "task": "T7",
            "error_class": "rate_limit",
            "reset": {"hour": "15:00", "timezone": "UTC"},
        }
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("running"), rate_limited])
        runtime = self._create_runtime(TASK_TO_DELIVER, create_forge(NO_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-18T09:00:00Z",
                    "event": "wave.started",
                    "wave": "tidepool_w16",
                    "project": "tidepool",
                    "branch": "integration/M4",
                    "tasks": ["T7"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "running",
                },
                {
                    "schema_version": 2,
                    "ts": "2026-10-19T08:50:00Z",
                    "event": "run.finished",
                    "run": ANY,
                    "segment": 1,
                    "procedure": "deliver",
                    "slot": "build",
                    "role": "builder",
                    "client": "fake",
                    "project": None,
                    "session": "session-b74",
                    "main_steps": 12,
                    "total_steps": 12,
                    "duration_ms": 4200,
                    "usage": None,
                    "outcome": "failed",
                    "error_class": "rate_limit",
                    "exit": 0,
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "nulls": {},
                    "message": "the task is delivered",
                    "reset": {
                        "hour": "15:00",
                        "timezone": "UTC",
                    },
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "wave.paused",
                    "wave": "tidepool_w16",
                    "reason": "quota",
                    "resume_at": "2026-10-19T15:00:00Z",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "paused:quota",
                },
            ],
        )

    def test_should_move_the_task_whose_run_hit_the_quota_to_paused_on_the_quota(self):
        # Arrange
        rate_limited = {
            **create_run_result(FIRST_RUN, "failed", "2026-10-19T08:50:00Z"),
            "wave": WAVE,
            "task": "T7",
            "error_class": "rate_limit",
        }
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("running"), rate_limited])
        runtime = self._create_runtime(TASK_TO_DELIVER, create_forge(NO_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-18T09:00:00Z",
                    "event": "wave.started",
                    "wave": "tidepool_w16",
                    "project": "tidepool",
                    "branch": "integration/M4",
                    "tasks": ["T7"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "running",
                },
                {
                    "schema_version": 2,
                    "ts": "2026-10-19T08:50:00Z",
                    "event": "run.finished",
                    "run": ANY,
                    "segment": 1,
                    "procedure": "deliver",
                    "slot": "build",
                    "role": "builder",
                    "client": "fake",
                    "project": None,
                    "session": "session-b74",
                    "main_steps": 12,
                    "total_steps": 12,
                    "duration_ms": 4200,
                    "usage": None,
                    "outcome": "failed",
                    "error_class": "rate_limit",
                    "exit": 0,
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "nulls": {},
                    "message": "the task is delivered",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "wave.paused",
                    "wave": "tidepool_w16",
                    "reason": "quota",
                    "resume_at": "2026-10-19T09:30:00Z",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "paused:quota",
                },
            ],
        )

    def test_should_record_the_wave_resumed_once_its_pause_on_the_quota_is_over(self):
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
        write_ledger(
            self.root, [WAVE_STARTED, finished, PAUSED_ON_THE_QUOTA_UNTIL_08, _record_task_state("paused:quota")]
        )
        runtime = self._create_runtime(TASK_TO_DELIVER, create_forge(NO_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-18T09:00:00Z",
                    "event": "wave.started",
                    "wave": "tidepool_w16",
                    "project": "tidepool",
                    "branch": "integration/M4",
                    "tasks": ["T7"],
                },
                {
                    "schema_version": 2,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "run.finished",
                    "run": ANY,
                    "segment": 1,
                    "procedure": "deliver",
                    "slot": "build",
                    "role": "builder",
                    "client": "fake",
                    "project": None,
                    "session": "session-b74",
                    "main_steps": 12,
                    "total_steps": 12,
                    "duration_ms": 4200,
                    "usage": None,
                    "outcome": "failed",
                    "error_class": None,
                    "exit": 0,
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "nulls": {},
                    "message": "the task is delivered",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T07:30:00Z",
                    "event": "wave.paused",
                    "wave": "tidepool_w16",
                    "reason": "quota",
                    "resume_at": "2026-10-19T08:00:00Z",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "paused:quota",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "wave.resumed",
                    "wave": "tidepool_w16",
                    "reason": "quota",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "running",
                },
            ],
        )

    def test_should_pause_the_wave_on_an_unavailable_forge_account_and_launch_none_of_its_tasks(self):
        # Arrange
        self.worktree.mkdir(parents=True)
        write_ledger(self.root, [WAVE_STARTED, FORGE_ACCOUNT_UNAVAILABLE])
        runtime = self._create_runtime(TASK_TO_DELIVER, create_forge(NO_PULL_REQUEST, NO_DETAILS_ASKED))
        no_launch = []

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-18T09:00:00Z",
                    "event": "wave.started",
                    "wave": "tidepool_w16",
                    "project": "tidepool",
                    "branch": "integration/M4",
                    "tasks": ["T7"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T08:00:00Z",
                    "event": "forge_account.unavailable",
                    "login": "octo-bot",
                    "key": "build",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "wave.paused",
                    "wave": "tidepool_w16",
                    "reason": "forge_account",
                    "resume_at": None,
                },
            ],
        )
        self.assertEqual(self.spawn.argvs, no_launch)

    def test_should_launch_the_tasks_of_a_wave_resumed_after_its_pause_on_the_forge_account(self):
        # Arrange
        self.worktree.mkdir(parents=True)
        write_ledger(
            self.root,
            [WAVE_STARTED, FORGE_ACCOUNT_UNAVAILABLE, PAUSED_ON_THE_FORGE_ACCOUNT, RESUMED_FROM_THE_FORGE_ACCOUNT],
        )
        runtime = self._create_runtime(TASK_TO_DELIVER, create_forge(NO_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self.spawn.argvs,
            [
                (
                    "run",
                    "build-task",
                    "task=@TASK.T7",
                    "base=integration/M4",
                    "--slot",
                    "build",
                    "--cwd",
                    f"{self.root}/tidepool/.brigade/worktrees/T7",
                    "--project",
                    "tidepool",
                    "--brief",
                    f"{self.root}/state/briefs/tidepool_w16-T7.md",
                    "--wave",
                    "tidepool_w16",
                    "--task",
                    "T7",
                    "--run-id",
                    ANY,
                )
            ],
        )

    def test_should_leave_open_a_pull_request_failing_its_preflight(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("pr_open"), TASK_PR_OPENED])
        failing_checks = {**PULL_REQUEST_DETAILS, "checks": [{"name": "ci", "verdict": "failure"}]}
        runtime = self._create_runtime(TASK_DELIVERED, create_forge(OPEN_PULL_REQUEST, failing_checks))

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-18T09:00:00Z",
                    "event": "wave.started",
                    "wave": "tidepool_w16",
                    "project": "tidepool",
                    "branch": "integration/M4",
                    "tasks": ["T7"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "pr_open",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T11:00:00Z",
                    "event": "task.pr_opened",
                    "project": "tidepool",
                    "task": "T7",
                    "wave": "tidepool_w16",
                    "branch": "task/M4/T7",
                    "pr": 42,
                    "login": "tidepool-bot",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.preflighted",
                    "project": "tidepool",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "pr": 42,
                    "head": "8885daa",
                    "checks": [
                        {
                            "name": "ancestry",
                            "verdict": "pass",
                            "findings": [],
                        },
                        {
                            "name": "checks",
                            "verdict": "fail",
                            "findings": ["ci: failure"],
                        },
                        {
                            "name": "corpus",
                            "verdict": "pass",
                            "findings": [],
                        },
                        {
                            "name": "promotion",
                            "verdict": "pass",
                            "findings": [],
                        },
                        {
                            "name": "untouched_files",
                            "verdict": "pass",
                            "findings": [],
                        },
                        {
                            "name": "privacy",
                            "verdict": "pass",
                            "findings": [],
                        },
                        {
                            "name": "body",
                            "verdict": "pass",
                            "findings": [],
                        },
                        {
                            "name": "size",
                            "verdict": "info",
                            "findings": ["0 files", "0 lines", "0 packages", "0 layers"],
                        },
                    ],
                },
            ],
        )

    def test_should_report_a_wave_whose_tasks_are_merged_or_parked(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("merged")])
        runtime = self._create_runtime(TASK_DELIVERED, create_forge(NO_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-18T09:00:00Z",
                    "event": "wave.started",
                    "wave": "tidepool_w16",
                    "project": "tidepool",
                    "branch": "integration/M4",
                    "tasks": ["T7"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "merged",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "order.started",
                    "project": "tidepool",
                    "kind": "study",
                    "order": "wave-report",
                    "run": ANY,
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "wave.reported",
                    "wave": "tidepool_w16",
                    "run": ANY,
                },
            ],
        )

    def test_should_detach_the_wave_report_run_the_wave_reported_names(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("merged")])
        runtime = self._create_runtime(TASK_DELIVERED, create_forge(NO_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        [[*_, reported_run]] = self.spawn.argvs
        self.assertEqual(self.spawn.argvs, [("study", "run", "wave-report", "--run-id", reported_run)])
        self.assertEqual(
            self._read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-18T09:00:00Z",
                    "event": "wave.started",
                    "wave": "tidepool_w16",
                    "project": "tidepool",
                    "branch": "integration/M4",
                    "tasks": ["T7"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "merged",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "order.started",
                    "project": "tidepool",
                    "kind": "study",
                    "order": "wave-report",
                    "run": reported_run,
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "wave.reported",
                    "wave": "tidepool_w16",
                    "run": reported_run,
                },
            ],
        )

    def test_should_deliver_the_pattern_whose_request_the_closed_wave_delivers(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("merged"), WAVE_REPORTED])
        (self.root / "config" / "patterns.awawa").write_text(
            'PATTERN CartTimeouts\n\tTITLE "the cart tests fail on a timeout"\n\tSTATUS ratified\n\tACTION wave\n',
            encoding="utf-8",
        )
        request_from_the_pattern = (
            "tidepool_r1",
            (("PROJECT", "@PROJECT.tidepool"), ("MILESTONE", "M4"), ("FROM", "@PATTERN.CartTimeouts")),
        )
        runtime = self._create_runtime(
            TASK_DELIVERED, create_forge(MERGED_PULL_REQUEST, NO_DETAILS_ASKED), requests=(request_from_the_pattern,)
        )

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            (self.root / "config" / "patterns.awawa").read_text(encoding="utf-8"),
            'PATTERN CartTimeouts\n\tTITLE "the cart tests fail on a timeout"\n\tSTATUS delivered\n\tACTION wave\n',
        )

    def test_should_close_a_reported_wave_once_its_integration_pull_request_is_merged(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("merged"), WAVE_REPORTED])
        runtime = self._create_runtime(TASK_DELIVERED, create_forge(MERGED_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-18T09:00:00Z",
                    "event": "wave.started",
                    "wave": "tidepool_w16",
                    "project": "tidepool",
                    "branch": "integration/M4",
                    "tasks": ["T7"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "merged",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T12:00:00Z",
                    "event": "wave.reported",
                    "wave": "tidepool_w16",
                    "run": None,
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "wave.closed",
                    "wave": "tidepool_w16",
                    "pr": 42,
                },
            ],
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
            "STUDY": {"triage": PAUSED_TRIAGE},
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"))},
            "TASK": {"T7": TASK_DELIVERED, "T8": TASK_AFTER_T7},
        }
        return create_test_runtime(
            create_test_paths(self.root),
            run_process=create_machine_double(corpus, MACHINE_OUTPUTS),
            spawn_process=self.spawn.spawn,
            resolve_plugin=create_plugin_resolution(STEP_COUNTING_PROBE, forge),
        )

    def _read_events(self) -> list[dict]:
        return list(
            map(json.loads, (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8").splitlines())
        )

    def test_should_merge_the_pull_request_by_the_method_of_the_project(self):
        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

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
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(forge.merges, [])

    def test_should_record_the_merge_with_the_login_it_ran_as_and_the_task_merged(self):
        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(
            self._read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-18T09:00:00Z",
                    "event": "wave.started",
                    "wave": "tidepool_w16",
                    "project": "tidepool",
                    "branch": "integration/M4",
                    "tasks": ["T7", "T8"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T11:00:00Z",
                    "event": "task.pr_opened",
                    "project": "tidepool",
                    "task": "T7",
                    "wave": "tidepool_w16",
                    "branch": "task/M4/T7",
                    "pr": 42,
                    "login": "tidepool-bot",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T11:30:00Z",
                    "event": "task.preflighted",
                    "project": "tidepool",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "pr": 42,
                    "head": "8885daa",
                    "checks": [],
                },
                {
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
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "verified",
                },
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
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T8",
                    "state": "running",
                },
            ],
        )

    def test_should_count_as_review_rounds_the_verdicts_of_the_merged_task_in_its_wave_alone(self):
        # Arrange
        write_ledger(self.root, [*LEDGER_OF_A_VERIFIED_TASK, OTHER_TASK_PASSED, SAME_TASK_PASSED_IN_ANOTHER_WAVE])

        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(
            self._read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-18T09:00:00Z",
                    "event": "wave.started",
                    "wave": "tidepool_w16",
                    "project": "tidepool",
                    "branch": "integration/M4",
                    "tasks": ["T7", "T8"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T11:00:00Z",
                    "event": "task.pr_opened",
                    "project": "tidepool",
                    "task": "T7",
                    "wave": "tidepool_w16",
                    "branch": "task/M4/T7",
                    "pr": 42,
                    "login": "tidepool-bot",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T11:30:00Z",
                    "event": "task.preflighted",
                    "project": "tidepool",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "pr": 42,
                    "head": "8885daa",
                    "checks": [],
                },
                {
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
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "verified",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T11:45:00Z",
                    "event": "task.verdict",
                    "project": "tidepool",
                    "wave": "tidepool_w16",
                    "task": "T8",
                    "pr": 43,
                    "head": "8885daa",
                    "verdict": "pass",
                    "findings": [],
                    "login": None,
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T11:45:00Z",
                    "event": "task.verdict",
                    "project": "tidepool",
                    "wave": "tidepool_w15",
                    "task": "T7",
                    "pr": 41,
                    "head": "8885daa",
                    "verdict": "pass",
                    "findings": [],
                    "login": None,
                },
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
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T8",
                    "state": "running",
                },
            ],
        )

    def test_should_start_the_dependent_of_the_merged_task_in_the_same_tick(self):
        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(
            self.spawn.argvs,
            [
                (
                    "run",
                    "build-task",
                    "task=@TASK.T8",
                    "base=integration/M4",
                    "--slot",
                    "build",
                    "--cwd",
                    str(self.root / "tidepool" / ".brigade" / "worktrees" / "T8"),
                    "--project",
                    "tidepool",
                    "--brief",
                    str(self.root / "state" / "briefs" / "tidepool_w16-T8.md"),
                    "--wave",
                    "tidepool_w16",
                    "--task",
                    "T8",
                    "--run-id",
                    ANY,
                )
            ],
        )


NO_PULL_REQUEST_FROM_ANY_BRANCH = {}
INTEGRATION_PULL_REQUEST_OPEN_INTO_MAIN = {
    "number": 206,
    "state": "open",
    "checks": [],
    "review": None,
    "behind": False,
    "head": "8885daa",
    "base": "main",
}
INTEGRATION_PULL_REQUEST_CLOSED = {**INTEGRATION_PULL_REQUEST_OPEN_INTO_MAIN, "state": "closed"}
INTEGRATION_PULL_REQUEST_OPEN_INTO_ANOTHER_BASE = {**INTEGRATION_PULL_REQUEST_OPEN_INTO_MAIN, "base": "develop"}


INTEGRATION_PULL_REQUEST_OPEN_INTO_THE_MILESTONE_BRANCH = INTEGRATION_PULL_REQUEST_OPEN_INTO_MAIN | {
    "base": "integration/tides"
}
TASK_OF_NO_MILESTONE_DELIVERED = (("STATUS", "implemented"), ("DELIVERED_BY", "42"))


class OpeningForgeDouble:
    def __init__(self, found_by_branch: dict):
        self.found_by_branch = found_by_branch
        self.opened = []

    def find_pull_request(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "pull_request": self.found_by_branch.get(request["branch"])}

    def open_pull_request(self, request: dict, runtime) -> dict:
        self.opened.append(request)
        return {"schema_version": 1, "url": "https://github.com/octo/tidepool/pull/77", "number": 77}

    def describe_account(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "login": "tidepool-cli"}

    def list_check_runs(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "check_runs": []}

    def list_pull_requests(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "pull_requests": []}

    def list_review_threads(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "threads": []}


def _resolve_the_collectors_beside(resolve_plugin, root: Path):
    places = locate_collectors(root, create_test_paths(root))
    check_runs = resolve_collector("check-runs", places)
    pr_threads = resolve_collector("pr-threads", places)

    def resolve(kind: str, name: str, **options):
        if (kind, name) == ("collector", "check-runs"):
            return check_runs
        if (kind, name) == ("collector", "pr-threads"):
            return pr_threads
        return resolve_plugin(kind, name, **options)

    return resolve


class TickOpeningTheIntegrationPullRequestTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        self.repository = self.root / "tidepool"
        self.forge = OpeningForgeDouble(NO_PULL_REQUEST_FROM_ANY_BRANCH)
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("merged"), CUT_OF_M4])
        self.runtime = self._create_runtime(self.forge)

    def _create_runtime(self, forge: OpeningForgeDouble, task: tuple = TASK_DELIVERED) -> Runtime:
        corpus = {
            "STUDY": {"triage": PAUSED_TRIAGE},
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"), ("FORGE", "github"))},
            "TASK": {"T7": task},
            "MILESTONE": {"M4": MILESTONE_M4},
        }
        return create_test_runtime(
            create_test_paths(self.root),
            run_process=create_machine_double(corpus, {**MACHINE_OUTPUTS, ("git", "ls-remote"): ""}),
            spawn_process=SpawnRecorderDouble().spawn,
            resolve_plugin=_resolve_the_collectors_beside(
                create_plugin_resolution(STEP_COUNTING_PROBE, forge), self.root
            ),
        )

    def _read_events(self) -> list[dict]:
        return list(
            map(json.loads, (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8").splitlines())
        )

    def test_should_open_the_pull_request_from_the_wave_branch_to_the_branch_of_its_milestone(self):
        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(
            self.forge.opened,
            [
                {
                    "repository": str(self.repository),
                    "base": "integration/tides",
                    "branch": "integration/M4",
                    "title": "chore(wave): merge the wave tidepool_w16 into integration/tides",
                    "body": "Integrates the wave tidepool_w16 of @PROJECT.tidepool into integration/tides: @TASK.T7.",
                    "milestone": None,
                    "environment": {},
                }
            ],
        )

    def test_should_record_the_opening_with_the_login_it_ran_as(self):
        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(
            self._read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-18T09:00:00Z",
                    "event": "wave.started",
                    "wave": "tidepool_w16",
                    "project": "tidepool",
                    "branch": "integration/M4",
                    "tasks": ["T7"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "merged",
                },
                CUT_OF_M4,
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "order.started",
                    "project": "tidepool",
                    "kind": "study",
                    "order": "wave-report",
                    "run": ANY,
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "wave.reported",
                    "wave": "tidepool_w16",
                    "run": ANY,
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "wave.pr_opened",
                    "wave": "tidepool_w16",
                    "pr": 77,
                    "login": "tidepool-cli",
                },
            ],
        )

    def test_should_open_none_at_a_second_tick(self):
        # Arrange
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(
            self.forge.opened,
            [
                {
                    "repository": f"{self.root}/tidepool",
                    "base": "integration/tides",
                    "branch": "integration/M4",
                    "title": "chore(wave): merge the wave tidepool_w16 into integration/tides",
                    "body": "Integrates the wave tidepool_w16 of @PROJECT.tidepool into integration/tides: @TASK.T7.",
                    "milestone": None,
                    "environment": {},
                }
            ],
        )

    def test_should_open_none_while_the_wave_branch_has_one_open_into_the_branch_of_its_milestone(self):
        # Arrange
        forge = OpeningForgeDouble({"integration/M4": INTEGRATION_PULL_REQUEST_OPEN_INTO_THE_MILESTONE_BRANCH})
        runtime = self._create_runtime(forge)

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(forge.opened, [])

    def test_should_record_as_opened_the_pull_request_already_open_into_the_milestone_branch_whoever_opened_it(self):
        # Arrange
        runtime = self._create_runtime(
            OpeningForgeDouble({"integration/M4": INTEGRATION_PULL_REQUEST_OPEN_INTO_THE_MILESTONE_BRANCH})
        )

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-18T09:00:00Z",
                    "event": "wave.started",
                    "wave": "tidepool_w16",
                    "project": "tidepool",
                    "branch": "integration/M4",
                    "tasks": ["T7"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "merged",
                },
                CUT_OF_M4,
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "order.started",
                    "project": "tidepool",
                    "kind": "study",
                    "order": "wave-report",
                    "run": ANY,
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "wave.reported",
                    "wave": "tidepool_w16",
                    "run": ANY,
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "wave.pr_opened",
                    "wave": "tidepool_w16",
                    "pr": 206,
                    "login": None,
                },
            ],
        )

    def test_should_open_its_own_beside_a_pull_request_of_the_wave_branch_closed_or_into_another_base(self):
        for found in [
            INTEGRATION_PULL_REQUEST_CLOSED,
            INTEGRATION_PULL_REQUEST_OPEN_INTO_ANOTHER_BASE,
            INTEGRATION_PULL_REQUEST_OPEN_INTO_MAIN,
        ]:
            with self.subTest(state=found["state"], base=found["base"]):
                # Arrange
                write_ledger(self.root, [WAVE_STARTED, _record_task_state("merged"), CUT_OF_M4])
                forge = OpeningForgeDouble({"integration/M4": found})
                runtime = self._create_runtime(forge)

                # Act
                COMMAND.run(Namespace(mode="once"), runtime)

                # Assert
                self.assertEqual(
                    forge.opened,
                    [
                        {
                            "repository": str(self.repository),
                            "base": "integration/tides",
                            "branch": "integration/M4",
                            "title": "chore(wave): merge the wave tidepool_w16 into integration/tides",
                            "body": "Integrates the wave tidepool_w16 of @PROJECT.tidepool into integration/tides: @TASK.T7.",
                            "milestone": None,
                            "environment": {},
                        }
                    ],
                )

    def test_should_open_the_pull_request_into_the_milestone_its_tasks_name_at_the_wave_branch_not_at_main(self):
        # Arrange
        (self.root / "cache" / "refs" / "tidepool" / MAIN_HEAD).mkdir(parents=True)
        wave_corpus = create_corpus_double(
            {
                "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"), ("FORGE", "github"))},
                "TASK": {"T7": TASK_DELIVERED},
                "MILESTONE": {"M4": MILESTONE_M4},
            }
        )
        main_corpus = create_corpus_double(
            {
                "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"), ("FORGE", "github"))},
                "TASK": {"T7": (("MILESTONE", "@MILESTONE.M5"), ("STATUS", "implemented"), ("DELIVERED_BY", "42"))},
                "MILESTONE": {"M4": MILESTONE_M4, "M5": (("STATUS", "active"), ("TITLE", "Currents"))},
            }
        )

        def answer_by_tree(request):
            if request.argv[:1] == ("awawa",) and MAIN_HEAD in request.argv[-1]:
                return main_corpus(request)
            return wave_corpus(request)

        answers = {
            **MACHINE_ANSWERS,
            ("git", "ls-remote"): ProcessAnswer(stdout=""),
            ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "origin/main^{commit}"): ProcessAnswer(
                stdout=f"{MAIN_HEAD}\n"
            ),
        }
        runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=ScriptedProcessRunner(answers, fallback=answer_by_tree).run,
            spawn_process=SpawnRecorderDouble().spawn,
            resolve_plugin=_resolve_the_collectors_beside(
                create_plugin_resolution(STEP_COUNTING_PROBE, self.forge), self.root
            ),
        )

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(self.forge.opened[0]["base"], "integration/tides")

    def test_should_record_the_cut_of_the_branch_of_the_milestone_with_the_login_of_the_cli(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("merged")])
        corpus = {
            "STUDY": {"triage": PAUSED_TRIAGE},
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"), ("FORGE", "github"))},
            "TASK": {"T7": TASK_DELIVERED},
            "MILESTONE": {"M4": MILESTONE_M4},
        }
        answers = {
            **MACHINE_ANSWERS,
            ("git", "ls-remote"): ProcessAnswer(stdout=""),
            ("git", "rev-parse", "--verify", "--quiet", "refs/heads/integration/tides"): ProcessAnswer(exit_code=1),
            ("git", "ls-remote", "--quiet", "--exit-code", "--heads", "origin", "refs/heads/integration/tides"): (
                ProcessAnswer(exit_code=2)
            ),
            ("git", "branch", "--quiet", "integration/tides"): ProcessAnswer(),
            ("git", "push", "--quiet", "origin", "integration/tides"): ProcessAnswer(),
        }
        runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=ScriptedProcessRunner(answers, fallback=create_corpus_double(corpus)).run,
            spawn_process=SpawnRecorderDouble().spawn,
            resolve_plugin=_resolve_the_collectors_beside(
                create_plugin_resolution(STEP_COUNTING_PROBE, self.forge), self.root
            ),
        )

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertIn({**CUT_OF_M4, "ts": ANY}, self._read_events())

    def test_should_open_the_pull_request_of_a_wave_of_tasks_naming_no_milestone_into_the_main_branch(self):
        # Arrange
        runtime = self._create_runtime(self.forge, TASK_OF_NO_MILESTONE_DELIVERED)

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(self.forge.opened[0]["base"], "main")


WAVE_PR_OPENED = {
    "schema_version": 1,
    "ts": "2026-10-18T12:30:00Z",
    "event": "wave.pr_opened",
    "wave": "tidepool_w16",
    "pr": 206,
    "login": "tidepool-cli",
}
WAVE_PULL_REQUEST_READY = INTEGRATION_PULL_REQUEST_OPEN_INTO_THE_MILESTONE_BRANCH | {
    "checks": [{"name": "tests", "verdict": "success"}]
}
NO_REVIEW_THREAD = []
UNRESOLVED_REVIEW_THREAD = [
    {"id": "PRRT_1", "file": "brigade/tick/plan.py", "line": 12, "author": "octo-reviewer", "body": "Why here?"}
]


class WaveMergingForgeDouble(OpeningForgeDouble):
    def __init__(self, found_by_branch: dict, threads: list[dict]):
        super().__init__(found_by_branch)
        self.threads = threads
        self.merges = []

    def list_review_threads(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "threads": self.threads}

    def merge_pull_request(self, request: dict, runtime) -> dict:
        self.merges.append(request)
        self.found_by_branch = {WAVE_BRANCH: WAVE_PULL_REQUEST_READY | {"state": "merged"}}
        return {"schema_version": 1}


class TickMergingThePullRequestOfAWaveTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        self.repository = self.root / "tidepool"
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("merged"), CUT_OF_M4, WAVE_REPORTED, WAVE_PR_OPENED])

    def _create_runtime(self, forge: WaveMergingForgeDouble) -> Runtime:
        corpus = {
            "STUDY": {"triage": PAUSED_TRIAGE},
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"), ("FORGE", "github"))},
            "TASK": {"T7": TASK_DELIVERED},
            "MILESTONE": {"M4": MILESTONE_M4},
        }
        return create_test_runtime(
            create_test_paths(self.root),
            run_process=create_machine_double(corpus, {**MACHINE_OUTPUTS, ("git", "ls-remote"): ""}),
            spawn_process=SpawnRecorderDouble().spawn,
            resolve_plugin=_resolve_the_collectors_beside(
                create_plugin_resolution(STEP_COUNTING_PROBE, forge), self.root
            ),
        )

    def _read_wave_events(self) -> list[dict]:
        return select_wave_events(
            map(json.loads, (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8").splitlines())
        )

    def test_should_merge_the_pull_request_of_the_wave_into_the_branch_of_its_milestone_on_the_gate(self):
        # Arrange
        forge = WaveMergingForgeDouble({WAVE_BRANCH: WAVE_PULL_REQUEST_READY}, NO_REVIEW_THREAD)

        # Act
        COMMAND.run(Namespace(mode="once"), self._create_runtime(forge))

        # Assert
        self.assertEqual(
            forge.merges, [{"repository": str(self.repository), "number": 206, "method": "rebase", "environment": {}}]
        )

    def test_should_record_the_merge_then_the_close_of_the_wave(self):
        # Arrange
        forge = WaveMergingForgeDouble({WAVE_BRANCH: WAVE_PULL_REQUEST_READY}, NO_REVIEW_THREAD)

        # Act
        COMMAND.run(Namespace(mode="once"), self._create_runtime(forge))

        # Assert
        self.assertEqual(
            self._read_wave_events(),
            [
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "wave.merged",
                    "wave": "tidepool_w16",
                    "pr": 206,
                    "login": "tidepool-cli",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "wave.closed",
                    "wave": "tidepool_w16",
                    "pr": 206,
                },
            ],
        )

    def test_should_merge_none_while_a_review_thread_of_it_is_unresolved(self):
        # Arrange
        forge = WaveMergingForgeDouble({WAVE_BRANCH: WAVE_PULL_REQUEST_READY}, UNRESOLVED_REVIEW_THREAD)

        # Act
        COMMAND.run(Namespace(mode="once"), self._create_runtime(forge))

        # Assert
        self.assertEqual(forge.merges, [])

    def test_should_merge_none_into_the_main_branch(self):
        # Arrange
        into_main = WAVE_PULL_REQUEST_READY | {"base": "main"}
        forge = WaveMergingForgeDouble({WAVE_BRANCH: into_main}, NO_REVIEW_THREAD)

        # Act
        COMMAND.run(Namespace(mode="once"), self._create_runtime(forge))

        # Assert
        self.assertEqual(forge.merges, [])


class TickStartingAndCuttingWavesTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        corpus = {
            "STUDY": {"triage": PAUSED_TRIAGE},
            "PROJECT": {"tidepool": (("PATH", str(self.root / "tidepool")), ("MAIN", "main"))},
            "TASK": {"T7": TASK_TO_DELIVER},
            "MILESTONE": {"M4": MILESTONE_M4},
        }
        outputs = {
            **MACHINE_ANSWERS,
            ("git", "branch", "--quiet"): ProcessAnswer(),
        }
        self.machine = ScriptedProcessRunner(outputs, fallback=create_corpus_double(corpus))
        self.runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=self.machine.run,
            spawn_process=SpawnRecorderDouble().spawn,
            resolve_plugin=create_plugin_resolution(
                STEP_COUNTING_PROBE, create_forge(NO_PULL_REQUEST, NO_DETAILS_ASKED)
            ),
        )

    def _miss_the_branch(self, branch: str) -> None:
        verify = ("git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}")
        self.machine.answers[verify] = ProcessAnswer(exit_code=1)

    def test_should_start_a_wave_of_the_candidates_of_a_project_without_one(self):
        # Arrange
        self._miss_the_branch("integration/tidepool_w1")
        self._miss_the_branch("integration/tides")

        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

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
        self.assertIn(("git", "branch", "--quiet", "integration/tidepool_w1", "integration/tides"), self.machine.argvs)

    def test_should_cut_the_missing_branch_of_an_open_wave(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED])
        self._miss_the_branch("integration/M4")
        self._miss_the_branch("integration/tides")

        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertIn(("git", "branch", "--quiet", "integration/M4", "integration/tides"), self.machine.argvs)

    def test_should_name_on_stderr_the_milestone_and_the_unrecorded_branch_it_refuses_to_cut(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED])
        self._miss_the_branch("integration/M4")
        errors = io.StringIO()

        # Act
        with contextlib.redirect_stderr(errors):
            COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertIn(
            "brigade tick: CutWaveBranch failed: @MILESTONE.M4: the branch integration/tides exists and no"
            " milestone.branch_cut records it\n",
            errors.getvalue(),
        )

    def test_should_name_on_stderr_the_milestone_branch_whose_rebase_run_ended_blocked_with_its_question(self):
        # Arrange
        blocked_run = {
            **create_run_record(FIRST_RUN, None, None),
            "slot": "rebase",
            "project": "tidepool",
            "worktree": str(self.root / "tidepool" / ".brigade" / "worktrees" / "integration-tides"),
        }
        blocked = {
            **create_run_result(FIRST_RUN, "blocked", "2026-10-18T10:00:00Z"),
            "message": "Keep the guard of plan.py or drop it?\nbrigade-end: blocked",
        }
        write_run(self.root / "state", blocked_run, blocked)
        write_ledger(self.root, [CUT_OF_M4, blocked])
        self.machine.answers[("git", "reset")] = ProcessAnswer()
        self.machine.answers[("git", "rev-parse", "HEAD")] = ProcessAnswer(stdout=f"{WAVE_HEAD}\n")
        self.machine.answers[("git", "rebase")] = ProcessAnswer()
        self.machine.answers[("git", "push")] = ProcessAnswer()
        errors = io.StringIO()

        # Act
        with contextlib.redirect_stderr(errors):
            COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertIn(
            "brigade tick: the rebase of integration/tides is blocked: Keep the guard of plan.py or drop it?\n",
            errors.getvalue(),
        )


OUTPUTS_OF_A_LAUNCH_STOPPED_ON_A_CONFLICT = {
    **MACHINE_ANSWERS,
    ("git", "merge-base", "--is-ancestor", "integration/M4", "task/M4/T7"): ProcessAnswer(exit_code=1),
    ("git", "rebase", "integration/M4"): ProcessAnswer(
        exit_code=1, stderr="CONFLICT (content): Merge conflict in src/tides.py"
    ),
    ("git", "rev-parse", "--quiet", "--verify", "REBASE_HEAD"): ProcessAnswer(stdout="f02da32\n"),
    ("git", "rebase", "--abort"): ProcessAnswer(),
}


class TickLaunchingATaskWhoseBranchConflictsWithTheWaveBranchTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        self.repository = self.root / "tidepool"
        self.worktree = self.repository / ".brigade" / "worktrees" / "T7"
        self.worktree.mkdir(parents=True)
        self.spawn = SpawnRecorderDouble()
        write_ledger(self.root, [WAVE_STARTED])
        corpus = {
            "STUDY": {"triage": PAUSED_TRIAGE},
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"))},
            "TASK": {"T7": TASK_TO_DELIVER},
        }
        self.runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=ScriptedProcessRunner(
                OUTPUTS_OF_A_LAUNCH_STOPPED_ON_A_CONFLICT, fallback=create_corpus_double(corpus)
            ).run,
            spawn_process=self.spawn.spawn,
            resolve_plugin=create_plugin_resolution(STEP_COUNTING_PROBE, RebasingForgeDouble([None])),
        )

    def test_should_launch_the_rebase_slot_on_the_worktree_of_the_task_instead_of_its_build(self):
        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(
            self.spawn.argvs,
            [
                (
                    "run",
                    "rebase-on-base",
                    "task=@TASK.T7",
                    "base=integration/M4",
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
        )

    def test_should_record_the_task_running(self):
        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        last_event = json.loads(
            (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8").splitlines()[-1]
        )
        self.assertEqual(
            last_event,
            {
                "schema_version": 1,
                "ts": ANY,
                "event": "task.state",
                "wave": "tidepool_w16",
                "task": "T7",
                "state": "running",
            },
        )


class TickLaunchingAStudyTest(unittest.TestCase):
    def test_should_launch_a_study_whose_schedule_is_due(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        spawn = SpawnRecorderDouble()
        runtime = create_test_runtime(
            create_test_paths(root),
            run_process=create_machine_double(
                {"STUDY": {"health": HEALTH_STUDY, "triage": PAUSED_TRIAGE}}, MACHINE_OUTPUTS
            ),
            spawn_process=spawn.spawn,
            resolve_plugin=create_plugin_resolution(STEP_COUNTING_PROBE),
        )

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(spawn.argvs, [("study", "run", "health", "--run-id", ANY)])

    def test_should_launch_the_built_in_triage_on_a_machine_that_never_ran_it(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        spawn = SpawnRecorderDouble()
        no_recorded_study = {}
        runtime = create_test_runtime(
            create_test_paths(root),
            run_process=create_machine_double(no_recorded_study, MACHINE_OUTPUTS),
            spawn_process=spawn.spawn,
            resolve_plugin=create_plugin_resolution(STEP_COUNTING_PROBE),
        )

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(spawn.argvs, [("study", "run", "triage", "--run-id", ANY)])


BEHIND_PULL_REQUEST = {**OPEN_PULL_REQUEST, "behind": True}
REBASED_HEAD = "9a9a9a9"
REBASED_PULL_REQUEST = {**OPEN_PULL_REQUEST, "head": REBASED_HEAD, "checks": [{"name": "ci", "verdict": "pending"}]}
REBASE_ONTO_THE_WAVE_BRANCH = ("git", "rebase", "origin/integration/M4")
FETCH_OF_THE_WAVE_BRANCH = ("git", "fetch", "--quiet", "origin", "integration/M4")
CLI_BOUND_TO_A_FORGE_ACCOUNT = '[forge_accounts]\ncli = "tidepool-cli"\n'
ENVIRONMENT_OF_THE_CLI_ACCOUNT = {"GH_TOKEN": "t0k3n"}
REBASE_OUTPUTS = {
    **MACHINE_ANSWERS,
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
            "STUDY": {"triage": PAUSED_TRIAGE},
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"))},
            "TASK": {"T7": TASK_DELIVERED},
        }
        self.machine = ScriptedProcessRunner(outputs, fallback=create_corpus_double(corpus))
        forge = RebasingForgeDouble(found)
        return create_test_runtime(
            create_test_paths(self.root),
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
        return list(
            map(json.loads, (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8").splitlines())
        )

    def test_should_rebase_the_task_branch_in_its_worktree_and_push_it_with_a_lease_on_its_head(self):
        # Arrange
        write_ledger(self.root, LEDGER_OF_A_TASK_IN_VERIFYING)
        runtime = self._create_runtime(REBASE_OUTPUTS, [BEHIND_PULL_REQUEST, REBASED_PULL_REQUEST])

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            select_argvs_opening_on(self.machine.argvs, GIT_REBASE, GIT_PUSH),
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
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-18T09:00:00Z",
                    "event": "wave.started",
                    "wave": "tidepool_w16",
                    "project": "tidepool",
                    "branch": "integration/M4",
                    "tasks": ["T7"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T11:00:00Z",
                    "event": "task.pr_opened",
                    "project": "tidepool",
                    "task": "T7",
                    "wave": "tidepool_w16",
                    "branch": "task/M4/T7",
                    "pr": 42,
                    "login": "tidepool-bot",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T11:30:00Z",
                    "event": "task.preflighted",
                    "project": "tidepool",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "pr": 42,
                    "head": "8885daa",
                    "checks": [],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "verifying",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.rebased",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "before": "8885daa",
                    "after": "9a9a9a9",
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
        COMMAND.run(Namespace(mode="once"), runtime)

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
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(self.environments_of_the_fetch, [ENVIRONMENT_OF_THE_CLI_ACCOUNT])

    def test_should_abort_a_conflicting_rebase_and_launch_the_rebase_slot_in_fixing(self):
        # Arrange
        write_ledger(self.root, LEDGER_OF_A_TASK_IN_VERIFYING)
        runtime = self._create_runtime(OUTPUTS_OF_A_REBASE_STOPPED_ON_A_CONFLICT, [BEHIND_PULL_REQUEST])

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            select_argvs_opening_on(self.machine.argvs, GIT_REBASE, GIT_PUSH),
            [REBASE_ONTO_THE_WAVE_BRANCH, ("git", "rebase", "--abort")],
        )
        self.assertEqual(
            self.spawn.argvs,
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
        )
        self.assertEqual(
            self._read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-18T09:00:00Z",
                    "event": "wave.started",
                    "wave": "tidepool_w16",
                    "project": "tidepool",
                    "branch": "integration/M4",
                    "tasks": ["T7"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T11:00:00Z",
                    "event": "task.pr_opened",
                    "project": "tidepool",
                    "task": "T7",
                    "wave": "tidepool_w16",
                    "branch": "task/M4/T7",
                    "pr": 42,
                    "login": "tidepool-bot",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T11:30:00Z",
                    "event": "task.preflighted",
                    "project": "tidepool",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "pr": 42,
                    "head": "8885daa",
                    "checks": [],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "verifying",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "fixing",
                },
            ],
        )

    def test_should_park_on_a_conflict_a_task_whose_repair_rounds_are_spent(self):
        # Arrange
        write_ledger(self.root, LEDGER_OF_A_TASK_PAST_ITS_ROUNDS)
        runtime = self._create_runtime(OUTPUTS_OF_A_REBASE_STOPPED_ON_A_CONFLICT, [BEHIND_PULL_REQUEST])

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(self.spawn.argvs, [("study", "run", "wave-report", "--run-id", ANY)])
        self.assertEqual(
            self._read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-18T09:00:00Z",
                    "event": "wave.started",
                    "wave": "tidepool_w16",
                    "project": "tidepool",
                    "branch": "integration/M4",
                    "tasks": ["T7"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T11:00:00Z",
                    "event": "task.pr_opened",
                    "project": "tidepool",
                    "task": "T7",
                    "wave": "tidepool_w16",
                    "branch": "task/M4/T7",
                    "pr": 42,
                    "login": "tidepool-bot",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T11:30:00Z",
                    "event": "task.preflighted",
                    "project": "tidepool",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "pr": 42,
                    "head": "8885daa",
                    "checks": [],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "verifying",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "fixing",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "fixing",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "verifying",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.parked",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "reason": "past 2 repair rounds",
                    "blockers": [],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "order.started",
                    "project": "tidepool",
                    "kind": "study",
                    "order": "wave-report",
                    "run": ANY,
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "wave.reported",
                    "wave": "tidepool_w16",
                    "run": ANY,
                },
            ],
        )


ONE_FORGE_ATTEMPT = "forge_attempts = 1\n"
CLI_BOUND_TO_A_TOKENLESS_ACCOUNT = '[forge_accounts]\ncli = "tidepool-tokenless"\n'
NO_TOKEN = None


def create_forge_of_the_cli(found: dict | None, environment: dict | None) -> ForgeDouble:
    return ForgeDouble(
        {
            "find_pull_request": lambda request: {"schema_version": 1, "pull_request": found},
            "read_login_environment": lambda request: {"schema_version": 1, "environment": environment},
        }
    )


class TickReadingAsTheForgeAccountOfTheCliTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        self.repository = self.root / "tidepool"

    def _create_runtime(self, binding: str, forge: ForgeDouble) -> Runtime:
        (self.root / "config" / "config.toml").write_text(
            CLIENT_AND_DOCUMENT_CONFIGURATION + ONE_FORGE_ATTEMPT + binding, encoding="utf-8"
        )
        corpus = {
            "STUDY": {"triage": PAUSED_TRIAGE},
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"))},
            "TASK": {"T7": TASK_TO_DELIVER},
        }
        return create_test_runtime(
            create_test_paths(self.root),
            run_process=create_machine_double(corpus, MACHINE_OUTPUTS),
            resolve_plugin=create_plugin_resolution(STEP_COUNTING_PROBE, forge),
        )

    def test_should_read_the_pull_request_of_a_running_task_as_the_login_of_the_key_cli(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("running")])
        forge = create_forge_of_the_cli(OPEN_PULL_REQUEST, ENVIRONMENT_OF_THE_CLI_ACCOUNT)
        runtime = self._create_runtime(CLI_BOUND_TO_A_FORGE_ACCOUNT, forge)

        # Act
        COMMAND.run(Namespace(mode="dry-run"), runtime)

        # Assert
        self.assertEqual(
            forge.list_requests("find_pull_request"),
            [
                {
                    "schema_version": 1,
                    "repository": str(self.repository),
                    "branch": "task/M4/T7",
                    "environment": {"GH_TOKEN": "t0k3n"},
                }
            ],
        )

    def test_should_read_the_token_of_the_login_of_the_key_cli_once_per_tick(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("running")])
        forge = create_forge_of_the_cli(OPEN_PULL_REQUEST, ENVIRONMENT_OF_THE_CLI_ACCOUNT)
        runtime = self._create_runtime(CLI_BOUND_TO_A_FORGE_ACCOUNT, forge)

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            forge.list_requests("read_login_environment"), [{"schema_version": 1, "login": "tidepool-cli"}]
        )

    def test_should_stop_on_the_login_of_the_key_cli_without_a_token(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("running")])
        forge = create_forge_of_the_cli(OPEN_PULL_REQUEST, NO_TOKEN)
        runtime = self._create_runtime(CLI_BOUND_TO_A_TOKENLESS_ACCOUNT, forge)

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(mode="dry-run"), runtime)

        # Assert
        self.assertEqual(
            str(raised.exception), "gh printed no token for the login tidepool-tokenless, bound to cli, after 1 attempt"
        )

    def test_should_plan_the_wave_while_it_follows_no_task(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED])
        forge = create_forge_of_the_cli(NO_PULL_REQUEST, NO_TOKEN)
        runtime = self._create_runtime(CLI_BOUND_TO_A_TOKENLESS_ACCOUNT, forge)

        # Act
        document = COMMAND.run(Namespace(mode="dry-run"), runtime)

        # Assert
        self.assertEqual(
            document["plan"],
            [{"project": "tidepool", "wave": "tidepool_w16", "branch": "integration/M4", "task": "T7"}],
        )


FAILED_BUILD_OF_OAK = {
    "pull_request": None,
    "branch": "main",
    "head": "4567def",
    "name": "build",
    "conclusion": "failure",
    "link": None,
}


class CheckRunsForgeDouble:
    def __init__(self, failing_repository: str):
        self.failing_repository = failing_repository

    def list_check_runs(self, request: dict, runtime) -> dict:
        if request["repository"] == self.failing_repository:
            raise CommandFailed(("gh", "api", "graphql"), 1, "HTTP 502")
        return {"schema_version": 1, "check_runs": [FAILED_BUILD_OF_OAK]}

    def read_job_steps(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "steps": None}

    def list_pull_requests(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "pull_requests": []}


class TickRecordingTheFailingCheckRunsTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        no_ledger_lines: list[dict] = []
        write_ledger(self.root, no_ledger_lines)
        (self.root / "cache" / "refs" / "elm" / WAVE_HEAD).mkdir(parents=True)
        (self.root / "cache" / "refs" / "oak" / WAVE_HEAD).mkdir(parents=True)
        self.signals = self.root / "state" / "inbox" / "signals.jsonl"
        self.signals.parent.mkdir(parents=True)
        self.signals.write_text("", encoding="utf-8")
        corpus = {
            "STUDY": {"triage": PAUSED_TRIAGE},
            "PROJECT": {
                "elm": (("PATH", "/srv/elm"), ("MAIN", "main"), ("FORGE", "github"), ("STATUS", "active")),
                "oak": (("PATH", "/srv/oak"), ("MAIN", "main"), ("FORGE", "github"), ("STATUS", "active")),
            },
        }
        paths = create_test_paths(self.root)
        self.runtime = create_test_runtime(
            paths,
            run_process=create_machine_double(corpus, {**MACHINE_OUTPUTS, ("git", "ls-remote"): ""}),
            resolve_plugin=create_plugin_resolver(
                {
                    ("forge", "github"): CheckRunsForgeDouble(failing_repository="/srv/elm"),
                    ("collector", "check-runs"): resolve_collector("check-runs", locate_collectors(self.root, paths)),
                    ("collector", "pr-threads"): resolve_collector("pr-threads", locate_collectors(self.root, paths)),
                }
            ),
        )

    def test_should_record_the_failing_check_runs_of_an_active_project_in_the_inbox(self):
        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(
            list(map(json.loads, self.signals.read_text(encoding="utf-8").splitlines())),
            [
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "recorded",
                    "kind": "check_run",
                    "project": "oak",
                    "fingerprint": "cr:oak:main:build:4567def",
                    "evidence": {
                        "pull_request": None,
                        "branch": "main",
                        "head": "4567def",
                        "name": "build",
                        "conclusion": "failure",
                        "link": None,
                        "first_failing_step": None,
                    },
                }
            ],
        )

    def test_should_record_the_forge_error_of_a_project_in_the_outcome_of_the_tick_and_serve_the_others(self):
        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(
            list(map(json.loads, (self.root / "state" / "ledger" / "2026-10.jsonl").read_text().splitlines())),
            [
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "tick.action_failed",
                    "action": "CollectCheckRuns",
                    "project": "elm",
                    "wave": None,
                    "task": None,
                    "error": "collector check-runs exited 1\ngh api graphql exited 1: HTTP 502",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "inbox.recorded",
                    "fingerprint": "cr:oak:main:build:4567def",
                    "kind": "check_run",
                    "project": "oak",
                },
            ],
        )

    def test_should_count_the_collection_of_each_project_among_the_actions_of_the_tick(self):
        # Act
        document = COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "mode": "once",
                "ts": "2026-10-19T09:00:00Z",
                "duration_ms": ANY,
                "actions_applied": 3,
                "actions_failed": 1,
                "heartbeat": str(self.root / "state" / "tick.json"),
            },
        )


PR_THREADS = BuiltInCollector(
    name="pr-threads", source="built-in", command="brigade.collectors.pr_threads", module=pr_threads
)
OPEN_PULL_REQUEST_BY_REPOSITORY = {"oak": 4, "elm": 7}
THREAD_BY_PULL_REQUEST = {
    4: {"id": "PRRT_oak4", "file": "src/cart.py", "line": 12, "author": "delairec", "body": "Name the total"},
    7: {"id": "PRRT_elm7", "file": "src/tree.py", "line": 3, "author": "delairec", "body": "Test the empty tree"},
}


def _refuse_the_listing(request: dict) -> dict:
    raise BrigadeError("gh: HTTP 502")


def _list_the_open_pull_request(request: dict) -> dict:
    return {
        "schema_version": 1,
        "pull_requests": [{"number": OPEN_PULL_REQUEST_BY_REPOSITORY[Path(request["repository"]).name]}],
    }


def create_connector_forge(list_pull_requests_of_elm) -> ForgeDouble:
    return ForgeDouble(
        {
            "list_pull_requests": lambda request: (
                list_pull_requests_of_elm(request)
                if Path(request["repository"]).name == "elm"
                else _list_the_open_pull_request(request)
            ),
            "list_check_runs": lambda request: {"schema_version": 1, "check_runs": []},
            "list_review_threads": lambda request: {
                "schema_version": 1,
                "threads": [THREAD_BY_PULL_REQUEST[request["number"]]],
            },
        }
    )


class TickRunningTheConnectorsTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "cache" / "refs" / "oak" / WAVE_HEAD).mkdir(parents=True)
        (self.root / "cache" / "refs" / "elm" / WAVE_HEAD).mkdir(parents=True)

    def _create_runtime(self, projects: dict, forge: ForgeDouble) -> Runtime:
        paths = create_test_paths(self.root)
        resolve_plugin = create_plugin_resolution(STEP_COUNTING_PROBE, forge)
        collectors = {
            "pr-threads": PR_THREADS,
            "check-runs": resolve_collector("check-runs", locate_collectors(self.root, paths)),
        }
        return create_test_runtime(
            paths,
            run_process=create_machine_double(
                {"PROJECT": projects, "STUDY": {"triage": PAUSED_TRIAGE}}, MACHINE_OUTPUTS
            ),
            resolve_plugin=lambda kind, name, **options: (
                collectors[name] if kind == "collector" else resolve_plugin(kind, name, **options)
            ),
        )

    def _describe_project(self, name: str) -> tuple:
        return (("PATH", str(self.root / name)), ("MAIN", "main"), ("FORGE", "github"), ("STATUS", "active"))

    def _read_state_file(self, *parts: str) -> str:
        return self.root.joinpath("state", *parts).read_text(encoding="utf-8")

    def test_should_record_the_review_threads_of_every_active_project_at_each_tick(self):
        # Arrange
        projects = {"elm": self._describe_project("elm"), "oak": self._describe_project("oak")}
        runtime = self._create_runtime(projects, create_connector_forge(_list_the_open_pull_request))

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_state_file("inbox", "signals.jsonl"),
            '{"schema_version": 1, "ts": "2026-10-19T09:00:00Z", "event": "recorded", "kind": "review_thread",'
            ' "project": "elm", "fingerprint": "rt:PRRT_elm7", "evidence": {"pull_request": 7, "path": "src/tree.py",'
            ' "line": 3, "author": "delairec", "comment": "Test the empty tree"}}\n'
            '{"schema_version": 1, "ts": "2026-10-19T09:00:00Z", "event": "recorded", "kind": "review_thread",'
            ' "project": "oak", "fingerprint": "rt:PRRT_oak4", "evidence": {"pull_request": 4, "path": "src/cart.py",'
            ' "line": 12, "author": "delairec", "comment": "Name the total"}}\n',
        )

    def test_should_record_the_forge_error_of_the_connector_in_the_outcome_of_the_tick_for_the_project(self):
        # Arrange
        projects = {"elm": self._describe_project("elm")}
        runtime = self._create_runtime(projects, create_connector_forge(_refuse_the_listing))

        # Act
        document = COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_state_file("ledger", "2026-10.jsonl"),
            '{"schema_version": 1, "ts": "2026-10-19T09:00:00Z", "event": "tick.action_failed",'
            ' "action": "CollectReviewThreads", "project": "elm", "wave": null, "task": null,'
            ' "error": "collector pr-threads exited 1\\ngh: HTTP 502"}\n',
        )
        self.assertEqual(document["actions_failed"], 1)

    def test_should_count_the_connector_actions_among_the_actions_applied(self):
        # Arrange
        projects = {"elm": self._describe_project("elm"), "oak": self._describe_project("oak")}
        runtime = self._create_runtime(projects, create_connector_forge(_list_the_open_pull_request))

        # Act
        document = COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(document["actions_applied"], 4)

    def test_should_plan_the_connector_actions_on_a_dry_run_and_apply_none(self):
        # Arrange
        projects = {"elm": self._describe_project("elm"), "oak": self._describe_project("oak")}
        runtime = self._create_runtime(projects, create_connector_forge(_list_the_open_pull_request))

        # Act
        document = COMMAND.run(Namespace(mode="dry-run"), runtime)

        # Assert
        self.assertEqual(
            document["plan"], [{"project": "elm"}, {"project": "elm"}, {"project": "oak"}, {"project": "oak"}]
        )
        self.assertFalse(self.root.joinpath("state", "inbox", "signals.jsonl").exists())

    def test_should_record_the_review_threads_of_the_other_projects_when_the_forge_fails_for_one(self):
        # Arrange
        projects = {"elm": self._describe_project("elm"), "oak": self._describe_project("oak")}
        runtime = self._create_runtime(projects, create_connector_forge(_refuse_the_listing))

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_state_file("inbox", "signals.jsonl"),
            '{"schema_version": 1, "ts": "2026-10-19T09:00:00Z", "event": "recorded", "kind": "review_thread",'
            ' "project": "oak", "fingerprint": "rt:PRRT_oak4", "evidence": {"pull_request": 4, "path": "src/cart.py",'
            ' "line": 12, "author": "delairec", "comment": "Name the total"}}\n',
        )


MILESTONE_BRANCH = "integration/tides"
WAVE_CLOSED = {
    "schema_version": 1,
    "ts": "2026-10-18T13:00:00Z",
    "event": "wave.closed",
    "wave": "tidepool_w16",
    "pr": 206,
}
MILESTONE_PR_OPENED = {
    "schema_version": 1,
    "ts": "2026-10-18T13:30:00Z",
    "event": "milestone.pr_opened",
    "project": "tidepool",
    "milestone": "M4",
    "pr": 77,
    "login": "tidepool-cli",
}
MILESTONE_PULL_REQUEST_MERGED = {**INTEGRATION_PULL_REQUEST_OPEN_INTO_MAIN, "number": 77, "state": "merged"}
TASK_OF_M4_TO_DELIVER = (("MILESTONE", "@MILESTONE.M4"), ("STATUS", "todo"))
TASK_OF_M5_DELIVERED = (("MILESTONE", "@MILESTONE.M5"), ("STATUS", "implemented"), ("DELIVERED_BY", "42"))
WAVE_OF_ANOTHER_PROJECT_STARTED = {
    **WAVE_STARTED,
    "wave": "reef_w3",
    "project": "reef",
    "branch": "integration/reef_w3",
}
WAVE_OF_ANOTHER_PROJECT_CLOSED = {**WAVE_CLOSED, "wave": "reef_w3", "pr": 12}
OPEN_WAVE_OF_M4_STARTED = {
    **WAVE_STARTED,
    "ts": "2026-10-18T14:00:00Z",
    "wave": "tidepool_w17",
    "branch": "integration/tidepool_w17",
    "tasks": ["T8"],
}
OPEN_WAVE_OF_M5_STARTED = {**OPEN_WAVE_OF_M4_STARTED, "tasks": ["T9"]}
OPEN_WAVE_OF_ANOTHER_PROJECT_STARTED = {**WAVE_OF_ANOTHER_PROJECT_STARTED, "ts": "2026-10-18T14:00:00Z"}
NO_OTHER_PROJECT = {}
MILESTONE_BRANCH_DELETED_FROM_THE_FORGE = CommandFailed(
    ("git", "fetch", "--quiet", "origin", MILESTONE_BRANCH), 128, "couldn't find remote ref integration/tides"
)


class TickOpeningThePullRequestOfAMilestoneTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        self.repository = self.root / "tidepool"
        self.forge = OpeningForgeDouble(NO_PULL_REQUEST_FROM_ANY_BRANCH)
        write_ledger(
            self.root,
            [WAVE_STARTED, _record_task_state("merged"), CUT_OF_M4, WAVE_REPORTED, WAVE_PR_OPENED, WAVE_CLOSED],
        )

    def _create_runtime(
        self, forge: OpeningForgeDouble, tasks: dict, answers: dict = MACHINE_ANSWERS, projects: dict = NO_OTHER_PROJECT
    ) -> Runtime:
        corpus = {
            "STUDY": {"triage": PAUSED_TRIAGE},
            "PROJECT": {
                "tidepool": (("PATH", str(self.repository)), ("MAIN", "main"), ("FORGE", "github")),
                **projects,
            },
            "TASK": tasks,
            "MILESTONE": {"M4": MILESTONE_M4, "M5": (("STATUS", "active"), ("TITLE", "Currents"))},
        }
        return create_test_runtime(
            create_test_paths(self.root),
            run_process=ScriptedProcessRunner(
                {**answers, ("git", "ls-remote"): ProcessAnswer(stdout="")}, fallback=create_corpus_double(corpus)
            ).run,
            spawn_process=SpawnRecorderDouble().spawn,
            resolve_plugin=_resolve_the_collectors_beside(
                create_plugin_resolution(STEP_COUNTING_PROBE, forge), self.root
            ),
        )

    def _read_milestone_events(self) -> list[dict]:
        return select_milestone_events(
            map(json.loads, (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8").splitlines())
        )

    def test_should_open_the_pull_request_of_the_milestone_branch_into_main_once_its_last_wave_is_closed(self):
        # Act
        COMMAND.run(Namespace(mode="once"), self._create_runtime(self.forge, {"T7": TASK_DELIVERED}))

        # Assert
        self.assertEqual(
            self.forge.opened,
            [
                {
                    "repository": str(self.repository),
                    "base": "main",
                    "branch": "integration/tides",
                    "title": "chore(milestone): merge the milestone M4 into main",
                    "body": "Merges the milestone M4 of @PROJECT.tidepool into main, its waves merged:"
                    " tidepool_w16 #206.",
                    "milestone": None,
                    "environment": {},
                }
            ],
        )

    def test_should_record_the_opening_with_the_login_of_the_cli(self):
        # Act
        COMMAND.run(Namespace(mode="once"), self._create_runtime(self.forge, {"T7": TASK_DELIVERED}))

        # Assert
        self.assertEqual(
            self._read_milestone_events(),
            [
                CUT_OF_M4,
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "milestone.pr_opened",
                    "project": "tidepool",
                    "milestone": "M4",
                    "pr": 77,
                    "login": "tidepool-cli",
                },
            ],
        )

    def test_should_open_none_at_a_second_tick(self):
        # Arrange
        runtime = self._create_runtime(self.forge, {"T7": TASK_DELIVERED})
        COMMAND.run(Namespace(mode="once"), runtime)

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(len(self.forge.opened), 1)

    def test_should_open_it_beside_the_pull_request_opened_for_another_milestone(self):
        for case, opened_elsewhere in [
            ("another milestone of the project", {**MILESTONE_PR_OPENED, "milestone": "M5"}),
            ("the milestone of the same name of another project", {**MILESTONE_PR_OPENED, "project": "reef"}),
        ]:
            with self.subTest(case=case):
                # Arrange
                write_ledger(
                    self.root,
                    [
                        WAVE_STARTED,
                        _record_task_state("merged"),
                        CUT_OF_M4,
                        WAVE_REPORTED,
                        WAVE_PR_OPENED,
                        WAVE_CLOSED,
                        opened_elsewhere,
                    ],
                )
                forge = OpeningForgeDouble(NO_PULL_REQUEST_FROM_ANY_BRANCH)

                # Act
                COMMAND.run(Namespace(mode="once"), self._create_runtime(forge, {"T7": TASK_DELIVERED}))

                # Assert
                self.assertEqual(
                    forge.opened,
                    [
                        {
                            "repository": str(self.repository),
                            "base": "main",
                            "branch": "integration/tides",
                            "title": "chore(milestone): merge the milestone M4 into main",
                            "body": "Merges the milestone M4 of @PROJECT.tidepool into main, its waves merged:"
                            " tidepool_w16 #206.",
                            "milestone": None,
                            "environment": {},
                        }
                    ],
                )

    def test_should_open_none_on_the_closed_wave_of_another_project(self):
        # Arrange
        write_ledger(self.root, [CUT_OF_M4, WAVE_OF_ANOTHER_PROJECT_STARTED, WAVE_OF_ANOTHER_PROJECT_CLOSED])

        # Act
        COMMAND.run(Namespace(mode="once"), self._create_runtime(self.forge, {"T7": TASK_DELIVERED}))

        # Assert
        self.assertEqual(self.forge.opened, [])

    def test_should_open_none_while_a_wave_of_the_milestone_whose_branch_is_missing_is_open(self):
        # Arrange
        write_ledger(
            self.root,
            [
                WAVE_STARTED,
                _record_task_state("merged"),
                CUT_OF_M4,
                WAVE_REPORTED,
                WAVE_PR_OPENED,
                WAVE_CLOSED,
                OPEN_WAVE_OF_M4_STARTED,
            ],
        )
        answers = {
            **MACHINE_ANSWERS,
            (
                "git",
                "ls-remote",
                "--quiet",
                "--exit-code",
                "--heads",
                "origin",
                "refs/heads/integration/tidepool_w17",
            ): (ProcessAnswer(exit_code=2)),
            ("git", "push", "--quiet", "origin", "integration/tidepool_w17"): ProcessAnswer(),
        }
        runtime = self._create_runtime(self.forge, {"T7": TASK_DELIVERED, "T8": TASK_DELIVERED}, answers)

        # Act
        with contextlib.redirect_stderr(io.StringIO()):
            COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(self.forge.opened, [])

    def test_should_open_it_beside_an_open_wave_of_no_task_of_the_milestone(self):
        for case, open_wave, tasks, projects in [
            (
                "another milestone of the project",
                OPEN_WAVE_OF_M5_STARTED,
                {"T9": TASK_OF_M5_DELIVERED},
                NO_OTHER_PROJECT,
            ),
            (
                "a task of the same name in another project",
                OPEN_WAVE_OF_ANOTHER_PROJECT_STARTED,
                {},
                {"reef": (("PATH", str(self.root / "reef")), ("MAIN", "main"), ("FORGE", "github"))},
            ),
        ]:
            with self.subTest(case=case):
                # Arrange
                (self.root / "cache" / "refs" / "reef" / WAVE_HEAD).mkdir(parents=True, exist_ok=True)
                write_ledger(
                    self.root,
                    [
                        WAVE_STARTED,
                        _record_task_state("merged"),
                        CUT_OF_M4,
                        WAVE_REPORTED,
                        WAVE_PR_OPENED,
                        WAVE_CLOSED,
                        open_wave,
                    ],
                )
                answers = {
                    **MACHINE_ANSWERS,
                    (
                        "git",
                        "ls-remote",
                        "--quiet",
                        "--exit-code",
                        "--heads",
                        "origin",
                        f"refs/heads/{open_wave['branch']}",
                    ): (ProcessAnswer(exit_code=2)),
                    ("git", "push", "--quiet", "origin", open_wave["branch"]): ProcessAnswer(),
                }
                forge = OpeningForgeDouble(NO_PULL_REQUEST_FROM_ANY_BRANCH)
                runtime = self._create_runtime(forge, {"T7": TASK_DELIVERED, **tasks}, answers, projects)

                # Act
                with contextlib.redirect_stderr(io.StringIO()):
                    COMMAND.run(Namespace(mode="once"), runtime)

                # Assert
                self.assertEqual(
                    forge.opened,
                    [
                        {
                            "repository": str(self.repository),
                            "base": "main",
                            "branch": "integration/tides",
                            "title": "chore(milestone): merge the milestone M4 into main",
                            "body": "Merges the milestone M4 of @PROJECT.tidepool into main, its waves merged:"
                            " tidepool_w16 #206.",
                            "milestone": None,
                            "environment": {},
                        }
                    ],
                )

    def test_should_skip_a_milestone_whose_branch_cannot_be_fetched(self):
        # Arrange
        answers = {
            **MACHINE_ANSWERS,
            ("git", "fetch", "--quiet", "origin", MILESTONE_BRANCH): MILESTONE_BRANCH_DELETED_FROM_THE_FORGE,
        }
        runtime = self._create_runtime(self.forge, {"T7": TASK_DELIVERED}, answers)
        reported = io.StringIO()

        # Act
        with contextlib.redirect_stderr(reported):
            COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertIn(
            f"brigade tick: the milestone M4 of tidepool skipped: {MILESTONE_BRANCH_DELETED_FROM_THE_FORGE}",
            reported.getvalue().splitlines(),
        )

    def test_should_open_it_beside_the_milestone_of_a_project_no_longer_registered(self):
        # Arrange
        write_ledger(
            self.root,
            [
                WAVE_STARTED,
                _record_task_state("merged"),
                CUT_OF_M4,
                WAVE_REPORTED,
                WAVE_PR_OPENED,
                WAVE_CLOSED,
                {**CUT_OF_M4, "project": "reef"},
            ],
        )

        # Act
        with contextlib.redirect_stderr(io.StringIO()):
            COMMAND.run(Namespace(mode="once"), self._create_runtime(self.forge, {"T7": TASK_DELIVERED}))

        # Assert
        self.assertEqual(
            self.forge.opened,
            [
                {
                    "repository": str(self.repository),
                    "base": "main",
                    "branch": "integration/tides",
                    "title": "chore(milestone): merge the milestone M4 into main",
                    "body": "Merges the milestone M4 of @PROJECT.tidepool into main, its waves merged:"
                    " tidepool_w16 #206.",
                    "milestone": None,
                    "environment": {},
                }
            ],
        )

    def test_should_open_none_while_a_task_of_the_milestone_is_todo_at_its_branch(self):
        # Arrange
        runtime = self._create_runtime(self.forge, {"T7": TASK_DELIVERED, "T8": TASK_OF_M4_TO_DELIVER})

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(self.forge.opened, [])

    def test_should_open_none_while_no_closed_wave_holds_a_task_of_the_milestone(self):
        # Arrange
        runtime = self._create_runtime(self.forge, {"T7": TASK_OF_M5_DELIVERED})

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(self.forge.opened, [])

    def test_should_record_the_close_of_the_milestone_once_its_pull_request_is_merged(self):
        # Arrange
        write_ledger(
            self.root,
            [
                WAVE_STARTED,
                _record_task_state("merged"),
                CUT_OF_M4,
                WAVE_REPORTED,
                WAVE_PR_OPENED,
                WAVE_CLOSED,
                MILESTONE_PR_OPENED,
            ],
        )
        forge = OpeningForgeDouble({MILESTONE_BRANCH: MILESTONE_PULL_REQUEST_MERGED})

        # Act
        COMMAND.run(Namespace(mode="once"), self._create_runtime(forge, {"T7": TASK_DELIVERED}))

        # Assert
        self.assertEqual(
            self._read_milestone_events(),
            [
                CUT_OF_M4,
                MILESTONE_PR_OPENED,
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "milestone.closed",
                    "project": "tidepool",
                    "milestone": "M4",
                    "pr": 77,
                },
            ],
        )

    def test_should_record_the_close_once_whatever_the_ticks_after_it(self):
        # Arrange
        write_ledger(
            self.root,
            [
                WAVE_STARTED,
                _record_task_state("merged"),
                CUT_OF_M4,
                WAVE_REPORTED,
                WAVE_PR_OPENED,
                WAVE_CLOSED,
                MILESTONE_PR_OPENED,
            ],
        )
        runtime = self._create_runtime(
            OpeningForgeDouble({MILESTONE_BRANCH: MILESTONE_PULL_REQUEST_MERGED}), {"T7": TASK_DELIVERED}
        )
        COMMAND.run(Namespace(mode="once"), runtime)

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_milestone_events(),
            [
                CUT_OF_M4,
                MILESTONE_PR_OPENED,
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "milestone.closed",
                    "project": "tidepool",
                    "milestone": "M4",
                    "pr": 77,
                },
            ],
        )

    def test_should_record_the_close_of_a_milestone_whose_branch_the_forge_deleted_at_the_merge(self):
        # Arrange
        write_ledger(
            self.root,
            [
                WAVE_STARTED,
                _record_task_state("merged"),
                CUT_OF_M4,
                WAVE_REPORTED,
                WAVE_PR_OPENED,
                WAVE_CLOSED,
                MILESTONE_PR_OPENED,
            ],
        )
        answers = {
            **MACHINE_ANSWERS,
            ("git", "fetch", "--quiet", "origin", MILESTONE_BRANCH): MILESTONE_BRANCH_DELETED_FROM_THE_FORGE,
        }
        runtime = self._create_runtime(
            OpeningForgeDouble({MILESTONE_BRANCH: MILESTONE_PULL_REQUEST_MERGED}), {"T7": TASK_DELIVERED}, answers
        )

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertIn(
            {
                "schema_version": 1,
                "ts": "2026-10-19T09:00:00Z",
                "event": "milestone.closed",
                "project": "tidepool",
                "milestone": "M4",
                "pr": 77,
            },
            self._read_milestone_events(),
        )
