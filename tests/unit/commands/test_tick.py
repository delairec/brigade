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
from brigade.runs.record_run_pid import record_run_pid
from brigade.runtime import Runtime
from brigade.system.collector_places import locate_collectors
from brigade.system.resolve_collector import BuiltInCollector, resolve_collector
from brigade.system.run_process import ProcessRecord, ProcessRequest
from tests.unit.commands.command_runtime import (
    ProcessAnswer,
    ScriptedProcessRunner,
    answer,
    answer_from_corpus,
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
from tests.unit.ledger_reader_double import LedgerReaderDouble
from tests.unit.plugin_double import PluginDouble
from tests.unit.select_argvs_opening_on import select_argvs_opening_on
from tests.unit.select_milestone_events import select_milestone_events
from tests.unit.select_reported_milestones import select_reported_milestones
from tests.unit.select_reported_tasks import select_reported_tasks
from tests.unit.spawned_process_double import SpawnedProcessDouble

GIT_PUSH = ("git", "push")
GIT_ADD = ("git", "add")
GIT_COMMIT = ("git", "commit")
STAGED_CHANGES_FOUND = 1
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
                "merge_commands": [],
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
                    "integration_branches": [],
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
                    "merge_commands": [],
                },
                "tick 2026-10-07T09:00:00Z: 2 actions applied, 1 failed in 250 ms",
            ),
            (
                "once, naming a merge the user runs",
                {
                    "mode": "once",
                    "ts": "2026-10-07T09:00:00Z",
                    "duration_ms": 250,
                    "actions_applied": 0,
                    "actions_failed": 0,
                    "merge_commands": ["git -C /srv/shop merge integration/cart"],
                },
                (
                    "tick 2026-10-07T09:00:00Z: 0 actions applied, 0 failed in 250 ms\n"
                    "to merge: git -C /srv/shop merge integration/cart"
                ),
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
TASK_TO_DELIVER = (("TITLE", "Tide table"), ("TYPE", "feat"), ("MILESTONE", "@MILESTONE.M4"), ("STATUS", "todo"))
TASK_DELIVERED = (
    ("TITLE", "Tide table"),
    ("TYPE", "feat"),
    ("MILESTONE", "@MILESTONE.M4"),
    ("STATUS", "implemented"),
    ("DELIVERED_BY", "42"),
)
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
CUT_OF_M4_ON_THE_WAVE_BRANCH = {**CUT_OF_M4, "branch": WAVE_BRANCH}
MACHINE_OUTPUTS = {
    ("git", "rev-parse", "--verify"): f"{WAVE_HEAD}\n",
    ("git", "cat-file", "-p"): ".brigade/worktrees/\n",
    ("git", "worktree", "add"): "",
    ("git", "worktree", "list"): "",
    ("git", "worktree", "remove"): "",
    ("git", "branch", "--quiet", "-D"): "",
    ("git", "merge-base"): "",
    ("git", "fetch"): "",
    ("git", "ls-remote"): "",
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
    "branch": "feature/T7-tide-table",
    "pr": 42,
    "login": "tidepool-bot",
}
TASK_PR_OPENED_IN_AN_EARLIER_WAVE = {
    "schema_version": 1,
    "ts": "2026-10-17T11:00:00Z",
    "event": "task.pr_opened",
    "project": "tidepool",
    "task": "T7",
    "wave": "tidepool_w15",
    "branch": "feature/T7-old-title",
    "pr": 42,
    "login": "earlier-bot",
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
    "updated_at": "2026-10-18T11:00:00Z",
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
TASK_PREFLIGHTED_ON_FAILING_CHECKS_AND_PRIVACY = {
    **TASK_PREFLIGHTED_AT_THE_HEAD,
    "checks": [
        {"name": "checks", "verdict": "fail", "findings": ["ci: failure", "coverage: failure"]},
        {"name": "privacy", "verdict": "fail", "findings": ["src/cart.py:12: an e-mail address"]},
    ],
}
PULL_REQUEST_DETAILS = {
    "head": "feature/T7-tide-table",
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
PAUSED_SCAN = (("SLOT", "none"), ("OUTPUT", "inbox"), ("ANSWER", "ANSWER"), ("STATUS", "paused"))
PAUSED_BUILT_IN_STUDIES = {
    "triage": PAUSED_TRIAGE,
    "mine_transcripts": PAUSED_TRIAGE,
    "corpus_lint_tidepool": PAUSED_SCAN,
    "corpus_fmt_tidepool": PAUSED_SCAN,
    "stale_branches_tidepool": PAUSED_SCAN,
    "worktrees_tidepool": PAUSED_SCAN,
    "corpus_lint_oak": PAUSED_SCAN,
    "corpus_fmt_oak": PAUSED_SCAN,
    "stale_branches_oak": PAUSED_SCAN,
    "worktrees_oak": PAUSED_SCAN,
    "corpus_lint_elm": PAUSED_SCAN,
    "corpus_fmt_elm": PAUSED_SCAN,
    "stale_branches_elm": PAUSED_SCAN,
    "worktrees_elm": PAUSED_SCAN,
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
            "list_check_runs": lambda request: {"schema_version": 1, "check_runs": []},
            "list_review_threads": lambda request: {"schema_version": 1, "threads": []},
            "list_pull_requests": lambda request: {"schema_version": 1, "pull_requests": []},
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
            "STUDY": PAUSED_BUILT_IN_STUDIES,
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"), ("FORGE", "github"), *setup)},
            "TASK": {"T7": task},
            "REQUEST": dict(requests),
        }
        return create_test_runtime(
            create_test_paths(self.root),
            run_process=create_machine_double(corpus, MACHINE_OUTPUTS),
            spawn_process=self.spawn.spawn,
            resolve_plugin=_resolve_the_collectors_beside(
                create_plugin_resolution(STEP_COUNTING_PROBE, forge), self.root
            ),
        )

    def _read_events(self) -> list[dict]:
        return list(
            map(json.loads, (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8").splitlines())
        )

    def test_should_launch_the_build_run_of_a_task_ready_to_start(self):
        # Arrange
        self.worktree.mkdir(parents=True)
        write_ledger(self.root, [CUT_OF_M4_ON_THE_WAVE_BRANCH, WAVE_STARTED])
        runtime = self._create_runtime(TASK_TO_DELIVER, create_forge(NO_PULL_REQUEST, NO_DETAILS_ASKED))

        # Act
        document = COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(document["actions_applied"], 3)
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
                    "event": "wave.closed",
                    "wave": "tidepool_w16",
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
        write_ledger(
            self.root, [WAVE_STARTED, _record_task_state("running"), finished, _record_task_state("paused:quota")]
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
        write_ledger(
            self.root, [WAVE_STARTED, _record_task_state("running"), finished, _record_task_state("paused:quota")]
        )
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
                    "reason": "resumed after the quota reset",
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
                    "event": "wave.closed",
                    "wave": "tidepool_w16",
                },
            ],
        )

    def test_should_record_the_merge_of_the_pull_request_of_a_queued_task_the_wave_tree_holds_implemented(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("queued")])
        corpus = {
            "STUDY": PAUSED_BUILT_IN_STUDIES,
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"), ("FORGE", "github"))},
            "TASK": {"T7": TASK_DELIVERED},
        }
        runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=create_machine_double(corpus, {**MACHINE_OUTPUTS, **WAVE_TREE_HOLDING_T7_IMPLEMENTED_OUTPUTS}),
            spawn_process=self.spawn.spawn,
            resolve_plugin=_resolve_the_collectors_beside(
                create_plugin_resolution(STEP_COUNTING_PROBE, create_forge(MERGED_PULL_REQUEST, NO_DETAILS_ASKED)),
                self.root,
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
                    "event": "wave.closed",
                    "wave": "tidepool_w16",
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
                    "branch": "feature/T7-tide-table",
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

    def test_should_carry_onto_the_wave_the_opening_of_the_pull_request_an_earlier_wave_of_its_task_opened(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("pr_open"), TASK_PR_OPENED_IN_AN_EARLIER_WAVE])
        runtime = self._create_runtime(TASK_DELIVERED, create_forge(OPEN_PULL_REQUEST, PULL_REQUEST_DETAILS))

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_events()[3],
            {
                "schema_version": 1,
                "ts": "2026-10-19T09:00:00Z",
                "event": "task.pr_opened",
                "project": "tidepool",
                "task": "T7",
                "wave": "tidepool_w16",
                "branch": "feature/T7-old-title",
                "pr": 42,
                "login": "earlier-bot",
            },
        )

    def test_should_preflight_on_its_wave_a_pull_request_an_earlier_wave_of_its_task_opened(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("pr_open"), TASK_PR_OPENED_IN_AN_EARLIER_WAVE])
        runtime = self._create_runtime(TASK_DELIVERED, create_forge(OPEN_PULL_REQUEST, PULL_REQUEST_DETAILS))

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(self._read_events()[4]["event"], "task.preflighted")
        self.assertEqual(self._read_events()[4]["wave"], "tidepool_w16")

    def test_should_leave_a_task_waiting_when_the_opening_of_another_wave_is_not_of_its_pull_request(self):
        for case, opening in [
            ("of another pull request", {**TASK_PR_OPENED_IN_AN_EARLIER_WAVE, "pr": 41}),
            ("of another project", {**TASK_PR_OPENED_IN_AN_EARLIER_WAVE, "project": "harbour"}),
        ]:
            with self.subTest(case=case):
                # Arrange
                ledger = [WAVE_STARTED, _record_task_state("pr_open"), opening]
                write_ledger(self.root, ledger)
                runtime = self._create_runtime(TASK_DELIVERED, create_forge(OPEN_PULL_REQUEST, PULL_REQUEST_DETAILS))

                # Act
                COMMAND.run(Namespace(mode="once"), runtime)

                # Assert
                self.assertEqual(self._read_events(), ledger)

    def test_should_not_carry_an_opening_onto_a_wave_already_holding_its_own(self):
        # Arrange
        write_ledger(
            self.root,
            [WAVE_STARTED, _record_task_state("pr_open"), TASK_PR_OPENED_IN_AN_EARLIER_WAVE, TASK_PR_OPENED],
        )
        runtime = self._create_runtime(TASK_DELIVERED, create_forge(OPEN_PULL_REQUEST, PULL_REQUEST_DETAILS))

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(self._read_events()[4]["event"], "task.preflighted")

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
                    "branch": "feature/T7-tide-table",
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
        deliver.write_text("---\ncapabilities: read\n---\nDeliver the task.\n", encoding="utf-8")
        (self.root / "config" / "config.toml").write_text(
            f'{CLIENT_AND_DOCUMENT_CONFIGURATION}[procedures]\nbuild = "{deliver}"\n', encoding="utf-8"
        )
        self.worktree.mkdir(parents=True)
        write_ledger(self.root, [CUT_OF_M4_ON_THE_WAVE_BRANCH, WAVE_STARTED])
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
                    "branch": "feature/T7-tide-table",
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

    def test_should_launch_the_check_repair_with_the_logs_and_the_other_findings_and_record_it_in_fixing(self):
        # Arrange
        self.worktree.mkdir(parents=True)
        write_ledger(
            self.root,
            [
                CUT_OF_M4_ON_THE_WAVE_BRANCH,
                WAVE_STARTED,
                TASK_PR_OPENED,
                TASK_PREFLIGHTED_ON_FAILING_CHECKS_AND_PRIVACY,
                _record_task_state("pr_open"),
            ],
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
            f"- Worktree: {self.worktree}, on the branch feature/T7-tide-table.\n"
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
            "\n"
            "The other findings of the preflight of the same head:\n"
            "\n"
            "## privacy\n"
            "\n"
            "- src/cart.py:12: an e-mail address\n"
            "\n"
            "The coverage check failed: remove each uncovered line, then write it again from a test that demands it,"
            " seen failing first; never write a test after the code it covers.\n",
        )
        self.assertEqual(
            self._read_events(),
            [
                CUT_OF_M4_ON_THE_WAVE_BRANCH,
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
                    "branch": "feature/T7-tide-table",
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
                        {
                            "name": "privacy",
                            "verdict": "fail",
                            "findings": ["src/cart.py:12: an e-mail address"],
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
                    "branch": "feature/T7-tide-table",
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
            "STUDY": PAUSED_BUILT_IN_STUDIES,
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"), ("FORGE", "github"))},
            "TASK": {"T7": TASK_TO_DELIVER},
        }
        runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=create_machine_double(corpus, {**MACHINE_OUTPUTS, **BLOCKING_QUESTION_OUTPUTS}),
            spawn_process=self.spawn.spawn,
            resolve_plugin=_resolve_the_collectors_beside(
                create_plugin_resolution(STEP_COUNTING_PROBE, create_forge(NO_PULL_REQUEST, NO_DETAILS_ASKED)),
                self.root,
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
                    "event": "wave.closed",
                    "wave": "tidepool_w16",
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
            self.root,
            [
                WAVE_STARTED,
                _record_task_state("running"),
                finished,
                PAUSED_ON_THE_QUOTA_UNTIL_08,
                _record_task_state("paused:quota"),
            ],
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
                    "schema_version": 1,
                    "ts": "2026-10-18T10:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "running",
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
                    "reason": "resumed after the quota reset",
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
            [
                CUT_OF_M4_ON_THE_WAVE_BRANCH,
                WAVE_STARTED,
                FORGE_ACCOUNT_UNAVAILABLE,
                PAUSED_ON_THE_FORGE_ACCOUNT,
                RESUMED_FROM_THE_FORGE_ACCOUNT,
            ],
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
                    "branch": "feature/T7-tide-table",
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

    def test_should_close_with_no_report_a_wave_whose_tasks_are_merged_or_parked(self):
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
                    "event": "wave.closed",
                    "wave": "tidepool_w16",
                },
            ],
        )

    def test_should_leave_ratified_the_pattern_whose_request_the_closed_wave_delivers(self):
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
            'PATTERN CartTimeouts\n\tTITLE "the cart tests fail on a timeout"\n\tSTATUS ratified\n\tACTION wave\n',
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
                },
            ],
        )


WAVE_OF_TWO_TASKS_STARTED = {**WAVE_STARTED, "tasks": ["T7", "T8"]}
TASK_AFTER_T7 = (
    ("TITLE", "Tide table"),
    ("TYPE", "feat"),
    ("MILESTONE", "@MILESTONE.M4"),
    ("STATUS", "todo"),
    ("AFTER", "@TASK.T7"),
)
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
    CUT_OF_M4_ON_THE_WAVE_BRANCH,
    WAVE_OF_TWO_TASKS_STARTED,
    TASK_PR_OPENED,
    TASK_PREFLIGHTED_AT_THE_HEAD,
    TASK_PASSED_AT_THE_HEAD,
    _record_task_state("verified"),
]
OTHER_TASK_PASSED = {**TASK_PASSED_AT_THE_HEAD, "task": "T8", "pr": 43}
SAME_TASK_PASSED_IN_ANOTHER_WAVE = {**TASK_PASSED_AT_THE_HEAD, "wave": "tidepool_w15", "pr": 41}


class ForgeWithNothingToCollectDouble:
    def list_check_runs(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "check_runs": []}

    def list_pull_requests(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "pull_requests": []}

    def list_review_threads(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "threads": []}


class MergingForgeDouble(ForgeWithNothingToCollectDouble):
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


class MergingForgeRefusingAMovedHeadDouble(MergingForgeDouble):
    def __init__(self, found_by_branch: dict, pushed_head: str):
        super().__init__(found_by_branch)
        self.pushed_head = pushed_head

    def merge_pull_request(self, request: dict, runtime) -> dict:
        if request["head"] != self.pushed_head:
            raise BrigadeError("gh pr merge failed: Head branch was modified. Review and try the merge again.")
        return super().merge_pull_request(request, runtime)


class TickMergingAVerifiedTaskTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        self.repository = self.root / "tidepool"
        (self.repository / ".brigade" / "worktrees" / "T8").mkdir(parents=True)
        self.spawn = SpawnRecorderDouble()
        self.forge = MergingForgeDouble({"feature/T7-tide-table": GREEN_PULL_REQUEST})
        write_ledger(self.root, LEDGER_OF_A_VERIFIED_TASK)
        self.runtime = self._create_runtime(self.forge)

    def _create_runtime(self, forge: MergingForgeDouble) -> Runtime:
        corpus = {
            "STUDY": PAUSED_BUILT_IN_STUDIES,
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"), ("FORGE", "github"))},
            "TASK": {"T7": TASK_DELIVERED, "T8": TASK_AFTER_T7},
        }
        return create_test_runtime(
            create_test_paths(self.root),
            run_process=create_machine_double(corpus, MACHINE_OUTPUTS),
            spawn_process=self.spawn.spawn,
            resolve_plugin=_resolve_the_collectors_beside(
                create_plugin_resolution(STEP_COUNTING_PROBE, forge), self.root
            ),
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
            [
                {
                    "repository": str(self.repository),
                    "number": 42,
                    "method": "rebase",
                    "head": "8885daa",
                    "environment": {},
                }
            ],
        )

    def test_should_record_a_merge_refused_because_the_head_moved_as_a_failed_action_and_no_merge(self):
        # Arrange
        forge = MergingForgeRefusingAMovedHeadDouble(
            {"feature/T7-tide-table": GREEN_PULL_REQUEST}, pushed_head="9010166"
        )

        # Act
        COMMAND.run(Namespace(mode="once"), self._create_runtime(forge))

        # Assert
        self.assertEqual(
            self._read_events()[len(LEDGER_OF_A_VERIFIED_TASK) :],
            [
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "tick.action_failed",
                    "action": "MergePullRequest",
                    "project": "tidepool",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "error": "gh pr merge failed: Head branch was modified. Review and try the merge again.",
                },
            ],
        )

    def test_should_print_the_merge_with_the_head_it_names_on_a_dry_run(self):
        # Act
        document = COMMAND.run(Namespace(mode="dry-run"), self.runtime)

        # Assert
        self.assertEqual(
            document["plan"],
            [
                {
                    "project": "tidepool",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "pr": 42,
                    "method": "rebase",
                    "head": "8885daa",
                },
                {"project": "tidepool"},
                {"project": "tidepool"},
            ],
        )

    def test_should_merge_nothing_when_the_login_the_merge_would_run_as_cannot_be_read(self):
        # Arrange
        forge = MergingForgeWithAnUnreadableAccountDouble({"feature/T7-tide-table": GREEN_PULL_REQUEST})
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
                CUT_OF_M4_ON_THE_WAVE_BRANCH,
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
                    "branch": "feature/T7-tide-table",
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
                CUT_OF_M4_ON_THE_WAVE_BRANCH,
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
                    "branch": "feature/T7-tide-table",
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
    "updated_at": "2026-10-18T11:00:00Z",
}


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


class TickCuttingTheBranchOfAMilestoneTest(unittest.TestCase):
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
            "STUDY": PAUSED_BUILT_IN_STUDIES,
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

    def test_should_record_the_cut_of_the_branch_of_the_milestone_with_the_login_of_the_cli(self):
        # Arrange
        write_ledger(self.root, [])
        corpus = {
            "STUDY": PAUSED_BUILT_IN_STUDIES,
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"), ("FORGE", "github"))},
            "TASK": {"T7": TASK_TO_DELIVER},
            "MILESTONE": {"M4": MILESTONE_M4},
        }
        answers = {
            **MACHINE_ANSWERS,
            ("git", "ls-remote"): ProcessAnswer(stdout=""),
            ("git", "rev-parse", "--verify", "--quiet", "refs/heads/integration/tides"): ProcessAnswer(exit_code=1),
            ("git", "ls-remote", "--quiet", "--exit-code", "--heads", "origin", "refs/heads/integration/tides"): (
                ProcessAnswer(exit_code=2)
            ),
            ("git", "branch", "--quiet", "integration/tides", "origin/main"): ProcessAnswer(),
            ("git", "push", "--quiet", "origin", "integration/tides"): ProcessAnswer(),
            ("git", "push", "--quiet", "origin", "origin/main:refs/heads/integration/tides"): ProcessAnswer(),
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


DIGEST_OF_T7_TO_DELIVER = "ea6114be5c96ba7d91c8603bbf8a7722c0fe6cab82bc413c1fa9476a8c24c2c8"
WAVE_PR_OPENED = {
    "schema_version": 1,
    "ts": "2026-10-18T12:30:00Z",
    "event": "wave.pr_opened",
    "wave": "tidepool_w16",
    "pr": 206,
    "login": "tidepool-cli",
}


class TickStartingAndCuttingWavesTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        corpus = {
            "STUDY": PAUSED_BUILT_IN_STUDIES,
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
            json.loads(ledger[1]),
            {
                "schema_version": 2,
                "ts": ANY,
                "event": "wave.started",
                "wave": "tidepool_w1",
                "project": "tidepool",
                "tasks": ["T7"],
                "task_digests": {"T7": DIGEST_OF_T7_TO_DELIVER},
            },
        )

    def test_should_cut_the_branch_of_the_milestone_a_todo_task_names_before_its_wave_starts(self):
        # Arrange
        self._miss_the_branch("integration/tides")

        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        ledger = (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(
            json.loads(ledger[0]),
            {
                "schema_version": 1,
                "ts": ANY,
                "event": "milestone.branch_cut",
                "project": "tidepool",
                "milestone": "M4",
                "branch": "integration/tides",
                "login": None,
            },
        )
        self.assertEqual(json.loads(ledger[1])["event"], "wave.started")

    def test_should_print_the_cut_of_the_milestone_branch_on_a_dry_run(self):
        # Act
        document = COMMAND.run(Namespace(mode="dry-run"), self.runtime)

        # Assert
        self.assertEqual(document["plan"], [{"project": "tidepool", "milestone": "M4", "branch": "integration/tides"}])

    def test_should_name_on_stderr_the_milestone_whose_unrecorded_branch_it_refuses_to_cut(self):
        # Arrange
        errors = io.StringIO()

        # Act
        with contextlib.redirect_stderr(errors):
            COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertIn(
            "brigade tick: CutMilestoneBranch failed: @MILESTONE.M4: the branch integration/tides exists and no"
            " milestone.branch_cut records it\n",
            errors.getvalue(),
        )


WAVE_STARTED_ON_T7_AS_ITS_RUN_READ = {**WAVE_STARTED, "task_digests": {"T7": DIGEST_OF_T7_TO_DELIVER}}
BUILD_RUN_OF_T7_BLOCKED_ON_A_QUESTION = {
    **create_run_result(FIRST_RUN, "blocked", "2026-10-18T10:00:00Z"),
    "wave": "tidepool_w16",
    "task": "T7",
    "message": "Which forge does the check run against?\nbrigade-end: blocked",
}


class TickServingATaskWhoseRunEndedBlockedOnAQuestionTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        corpus = {
            "STUDY": PAUSED_BUILT_IN_STUDIES,
            "PROJECT": {"tidepool": (("PATH", str(self.root / "tidepool")), ("MAIN", "main"))},
            "TASK": {"T7": TASK_TO_DELIVER},
            "MILESTONE": {"M4": MILESTONE_M4},
        }
        machine = ScriptedProcessRunner(MACHINE_ANSWERS, fallback=create_corpus_double(corpus))
        self.runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=machine.run,
            spawn_process=SpawnRecorderDouble().spawn,
            resolve_plugin=create_plugin_resolution(
                STEP_COUNTING_PROBE, create_forge(NO_PULL_REQUEST, NO_DETAILS_ASKED)
            ),
        )
        blocked_run = {**create_run_record(FIRST_RUN, "tidepool_w16", "T7"), "project": "tidepool"}
        write_run(self.root / "state", blocked_run, BUILD_RUN_OF_T7_BLOCKED_ON_A_QUESTION)
        write_ledger(
            self.root,
            [
                CUT_OF_M4,
                WAVE_STARTED_ON_T7_AS_ITS_RUN_READ,
                _record_task_state("running"),
                BUILD_RUN_OF_T7_BLOCKED_ON_A_QUESTION,
            ],
        )

    def _read_ledger_text(self) -> str:
        return (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8")

    def test_should_start_no_second_wave_for_the_same_blocked_task_over_two_ticks(self):
        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(self._read_ledger_text().count('"event": "wave.started"'), 1)

    def test_should_park_the_task_on_the_question_and_close_its_wave(self):
        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertIn("blocked: Which forge does the check run against?", self._read_ledger_text())
        self.assertIn('"event": "wave.closed"', self._read_ledger_text())


MILESTONE_BRANCH_DESCENT = ("git", "merge-base", "--is-ancestor", "main", "integration/tides")
FORGE_MILESTONE_BRANCH_DESCENT = ("git", "merge-base", "--is-ancestor", "origin/main", "origin/integration/tides")
REBASE_OF_THE_MILESTONE_BRANCH = ("git", "rebase", "--fork-point", "main")
FORGE_REBASE_OF_THE_MILESTONE_BRANCH = ("git", "rebase", "--fork-point", "origin/main")
REBASE_OF_THE_WAVE_BRANCH = ("git", "rebase", "--fork-point", "integration/tides")
OUTPUTS_OF_A_MILESTONE_BRANCH_MAIN_HAS_OUTRUN = {
    **MACHINE_ANSWERS,
    ("git", "branch", "--quiet"): ProcessAnswer(),
    ("git", "reset"): ProcessAnswer(),
    ("git", "rev-parse", "HEAD"): ProcessAnswer(stdout=f"{WAVE_HEAD}\n"),
    REBASE_OF_THE_MILESTONE_BRANCH: ProcessAnswer(),
    ("git", "rev-parse", "--quiet", "--verify", "REBASE_HEAD"): ProcessAnswer(stdout="f02da32\n"),
    ("git", "rebase", "--abort"): ProcessAnswer(),
    ("awawa", "fmt", "--check", "."): ProcessAnswer(),
    ("awawa", "lint", "--strict", "."): ProcessAnswer(),
}
NO_ACTIVE_MILESTONE = ProcessAnswer(stdout='{"entities": []}')
BLOCKED_REBASE_OF_THE_MILESTONE_BRANCH = {
    **create_run_result(FIRST_RUN, "blocked", "2026-10-18T10:00:00Z"),
    "message": "Keep the guard of plan.py or drop it?\nbrigade-end: blocked",
}
LAUNCH_OF_THE_BLOCKED_REBASE_RUN_ON_THE_HEADS_THAT_STAND = {
    "schema_version": 1,
    "ts": "2026-10-18T09:45:00Z",
    "event": "milestone.rebase_launched",
    "project": "tidepool",
    "milestone": "M4",
    "branch": "integration/tides",
    "run": FIRST_RUN,
    "main_head": "8885daa",
    "branch_head": "8885daa",
}
LAUNCH_OF_THE_BLOCKED_REBASE_RUN_BEFORE_MAIN_MOVED = {
    **LAUNCH_OF_THE_BLOCKED_REBASE_RUN_ON_THE_HEADS_THAT_STAND,
    "main_head": "4c1d2e0",
}
NO_LAUNCH_RECORDED = ()


class MilestoneBranchRebasingRunnerDouble(ScriptedProcessRunner):
    def __init__(self, answers: dict, fallback, rebase: tuple, descent: tuple):
        super().__init__({**answers, descent: ProcessAnswer(exit_code=1)}, fallback)
        self.head_after_rebase = WAVE_HEAD
        self.rebase = rebase
        self.descent = descent

    def run(self, request):
        record = super().run(request)
        if request.argv == self.rebase and record.exit_code == 0:
            self.answers[self.descent] = ProcessAnswer()
            self.answers[("git", "rev-parse", "HEAD")] = ProcessAnswer(stdout=f"{self.head_after_rebase}\n")
        return record


class TickRebasingAMilestoneBranchMainHasOutrunTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        self.worktree = self.root / "tidepool" / ".brigade" / "worktrees" / "integration-tides"
        self.worktree.mkdir(parents=True)
        write_ledger(self.root, [CUT_OF_M4])
        self.spawn = SpawnRecorderDouble()
        self._create_runtime()

    def _create_runtime(self, forge: tuple = (), answers: dict | None = None, red_branch: str | None = None):
        corpus = {
            "STUDY": PAUSED_BUILT_IN_STUDIES,
            "PROJECT": {"tidepool": (("PATH", str(self.root / "tidepool")), ("MAIN", "main"), *forge)},
            "TASK": {"T7": TASK_TO_DELIVER},
            "MILESTONE": {"M4": MILESTONE_M4},
        }
        self.machine = MilestoneBranchRebasingRunnerDouble(
            {
                **OUTPUTS_OF_A_MILESTONE_BRANCH_MAIN_HAS_OUTRUN,
                ("git", "rev-parse", "--verify", "--quiet", "refs/heads/integration/tidepool_w1"): ProcessAnswer(
                    exit_code=1
                ),
                **(answers or {}),
            },
            fallback=create_corpus_double(corpus),
            rebase=FORGE_REBASE_OF_THE_MILESTONE_BRANCH if forge else REBASE_OF_THE_MILESTONE_BRANCH,
            descent=FORGE_MILESTONE_BRANCH_DESCENT if forge else MILESTONE_BRANCH_DESCENT,
        )
        forge_double = (
            OpeningForgeDouble(NO_PULL_REQUEST_FROM_ANY_BRANCH)
            if forge
            else create_forge(NO_PULL_REQUEST, NO_DETAILS_ASKED)
        )
        forge_name = dict(forge).get("FORGE", "github")
        self.runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=create_the_worktree_at_its_addition(self.machine.run),
            spawn_process=self.spawn.spawn,
            resolve_plugin=_serve_the_forge_double_as(
                forge_name,
                _resolve_the_collectors_beside(
                    create_plugin_resolution(STEP_COUNTING_PROBE, RedBranchForgeDouble(forge_double, red_branch)),
                    self.root,
                ),
            ),
        )

    def _stop_the_rebase_on_a_conflict(self) -> None:
        self.machine.answers[REBASE_OF_THE_MILESTONE_BRANCH] = ProcessAnswer(
            exit_code=1, stderr="CONFLICT (content): Merge conflict in src/tides.py"
        )

    def _block_the_last_rebase_run(
        self, launches: tuple[dict, ...] = (LAUNCH_OF_THE_BLOCKED_REBASE_RUN_ON_THE_HEADS_THAT_STAND,)
    ) -> None:
        blocked_run = {
            **create_run_record(FIRST_RUN, None, None),
            "slot": "rebase",
            "project": "tidepool",
            "worktree": str(self.worktree),
        }
        write_run(self.root / "state", blocked_run, BLOCKED_REBASE_OF_THE_MILESTONE_BRANCH)
        write_ledger(self.root, [CUT_OF_M4, *launches, BLOCKED_REBASE_OF_THE_MILESTONE_BRANCH])

    def test_should_name_on_stderr_the_red_main_branch_holding_the_rebase_of_the_milestone_branch(self):
        # Arrange
        write_commit_checks(self.root, WAVE_HEAD, FAILED)
        errors = io.StringIO()

        # Act
        with contextlib.redirect_stderr(errors):
            COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertIn(
            f"brigade tick: the rebase of integration/tides waits: main is red at {WAVE_HEAD}, `make test` failed\n",
            errors.getvalue(),
        )
        self.assertNotIn(REBASE_OF_THE_MILESTONE_BRANCH, self.machine.argvs)

    def test_should_hold_the_rebase_of_the_milestone_branch_on_the_check_runs_the_forge_of_the_project_lists(self):
        # Arrange
        self._create_runtime(
            forge=(("FORGE", FORGE_OF_NO_GITHUB),),
            answers={("git", "ls-remote"): ProcessAnswer(exit_code=2)},
            red_branch="main",
        )
        errors = io.StringIO()

        # Act
        with contextlib.redirect_stderr(errors):
            COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertIn(
            f"brigade tick: the rebase of integration/tides waits: main is red at {WAVE_HEAD}, `ci / tests` failed\n",
            errors.getvalue(),
        )

    def test_should_launch_one_run_repairing_the_red_main_branch_on_a_fix_branch_cut_from_its_head(self):
        # Arrange
        write_commit_checks(self.root, WAVE_HEAD, FAILED)
        repair = self.root / "tidepool" / ".brigade" / "worktrees" / f"fix-repair-main-{WAVE_HEAD}"

        # Act
        with contextlib.redirect_stderr(io.StringIO()):
            COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(
            select_argvs_opening_on(self.machine.argvs, ("git", "worktree", "add", "--quiet", "-b")),
            [("git", "worktree", "add", "--quiet", "-b", f"fix/repair-main-{WAVE_HEAD}", str(repair), WAVE_HEAD)],
        )
        self.assertEqual(
            self.spawn.argvs,
            [
                (
                    "run",
                    "rebase-on-base",
                    f"branch=fix/repair-main-{WAVE_HEAD}",
                    f"head={WAVE_HEAD}",
                    "into=main",
                    "--slot",
                    "rebase",
                    "--cwd",
                    str(repair),
                    "--project",
                    "tidepool",
                    "--run-id",
                    ANY,
                )
            ],
        )

    def test_should_rebase_the_milestone_branch_onto_main_before_the_wave_of_its_candidates_starts_on_it(self):
        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        ledger = (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(
            json.loads(ledger[1]),
            {
                "schema_version": 2,
                "ts": ANY,
                "event": "wave.started",
                "wave": "tidepool_w1",
                "project": "tidepool",
                "tasks": ["T7"],
                "task_digests": {"T7": DIGEST_OF_T7_TO_DELIVER},
            },
        )
        self.assertIn(REBASE_OF_THE_MILESTONE_BRANCH, self.machine.argvs)

    def test_should_record_the_rebase_of_the_milestone_branch_with_its_heads_before_and_after(self):
        # Arrange
        self.machine.head_after_rebase = "9b41d08"

        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        ledger = (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(
            json.loads(ledger[1]),
            {
                "schema_version": 1,
                "ts": ANY,
                "event": "milestone.rebased",
                "project": "tidepool",
                "milestone": "M4",
                "branch": "integration/tides",
                "before": "8885daa",
                "after": "9b41d08",
                "waves": [],
                "login": None,
            },
        )

    def test_should_record_the_rebase_of_the_milestone_branch_of_a_forge_with_the_login_of_the_cli(self):
        # Arrange
        self._create_runtime(
            forge=(("FORGE", "github"),),
            answers={
                FORGE_REBASE_OF_THE_MILESTONE_BRANCH: ProcessAnswer(),
                ("git", "push", "--quiet", f"--force-with-lease=integration/tides:{WAVE_HEAD}"): ProcessAnswer(),
                ("git", "ls-remote"): ProcessAnswer(exit_code=2),
                ("git", "push", "--quiet", "origin"): ProcessAnswer(),
            },
        )
        self.machine.head_after_rebase = "9b41d08"

        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        ledger = (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(
            json.loads(ledger[1]),
            {
                "schema_version": 1,
                "ts": ANY,
                "event": "milestone.rebased",
                "project": "tidepool",
                "milestone": "M4",
                "branch": "integration/tides",
                "before": "8885daa",
                "after": "9b41d08",
                "waves": [],
                "login": "tidepool-cli",
            },
        )

    def test_should_record_no_rebase_of_the_milestone_branch_whose_head_the_rebase_left_where_it_was(self):
        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        ledger = (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8")
        self.assertNotIn('"event": "milestone.rebased"', ledger)

    def test_should_rebase_no_milestone_branch_whose_milestone_is_no_longer_active(self):
        # Arrange
        self.machine.answers[("awawa", "status", "MILESTONE")] = NO_ACTIVE_MILESTONE

        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertNotIn(REBASE_OF_THE_MILESTONE_BRANCH, self.machine.argvs)

    def test_should_launch_a_rebase_run_on_the_worktree_of_the_milestone_branch_stopped_on_a_conflict(self):
        # Arrange
        self._stop_the_rebase_on_a_conflict()

        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(
            self.spawn.argvs[0],
            (
                "run",
                "rebase-on-base",
                "base=main",
                "--slot",
                "rebase",
                "--cwd",
                str(self.worktree),
                "--project",
                "tidepool",
                "--run-id",
                ANY,
            ),
        )

    def test_should_launch_no_second_rebase_run_while_the_first_lives(self):
        # Arrange
        self._stop_the_rebase_on_a_conflict()
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(self.machine.argvs.count(REBASE_OF_THE_MILESTONE_BRANCH), 1)

    def test_should_rebase_no_open_wave_branch_whose_worktree_a_live_run_holds(self):
        # Arrange
        write_ledger(self.root, [CUT_OF_M4, WAVE_STARTED])
        self.machine.answers[("git", "merge-base", "--is-ancestor", "integration/tides", "HEAD")] = ProcessAnswer(
            exit_code=1
        )
        self.machine.answers[REBASE_OF_THE_WAVE_BRANCH] = ProcessAnswer()
        live_run = {
            **create_run_record(FIRST_RUN, "tidepool_w16", "T7"),
            "cwd": str(self.root / "tidepool" / ".brigade" / "worktrees" / "integration-M4"),
        }
        record_run_pid(write_run(self.root / "state", live_run, None), os.getpid())

        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertIn(REBASE_OF_THE_MILESTONE_BRANCH, self.machine.argvs)
        self.assertNotIn(REBASE_OF_THE_WAVE_BRANCH, self.machine.argvs)

    def test_should_record_the_launch_of_the_rebase_run_of_the_milestone_branch_with_the_heads_it_starts_from(self):
        # Arrange
        self._stop_the_rebase_on_a_conflict()

        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        ledger = (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(
            json.loads(ledger[1]),
            {
                "schema_version": 1,
                "ts": ANY,
                "event": "milestone.rebase_launched",
                "project": "tidepool",
                "milestone": "M4",
                "branch": "integration/tides",
                "run": self.spawn.argvs[0][-1],
                "main_head": "8885daa",
                "branch_head": "8885daa",
            },
        )

    def test_should_rebase_no_milestone_branch_whose_rebase_run_ended_blocked_on_the_heads_that_stand(self):
        # Arrange
        self._block_the_last_rebase_run()

        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertNotIn(REBASE_OF_THE_MILESTONE_BRANCH, self.machine.argvs)

    def test_should_rebase_again_the_milestone_branch_whose_rebase_run_ended_blocked_once_main_moved(self):
        # Arrange
        self._block_the_last_rebase_run((LAUNCH_OF_THE_BLOCKED_REBASE_RUN_BEFORE_MAIN_MOVED,))

        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertIn(REBASE_OF_THE_MILESTONE_BRANCH, self.machine.argvs)

    def test_should_rebase_again_the_milestone_branch_whose_blocked_rebase_run_recorded_no_heads(self):
        # Arrange
        self._block_the_last_rebase_run(NO_LAUNCH_RECORDED)

        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertIn(REBASE_OF_THE_MILESTONE_BRANCH, self.machine.argvs)

    def test_should_name_on_stderr_the_milestone_branch_whose_rebase_run_ended_blocked_with_its_question(self):
        # Arrange
        self._block_the_last_rebase_run()
        errors = io.StringIO()

        # Act
        with contextlib.redirect_stderr(errors):
            COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertIn(
            "brigade tick: the rebase of integration/tides is blocked: Keep the guard of plan.py or drop it?\n",
            errors.getvalue(),
        )

    def test_should_name_no_milestone_branch_main_no_longer_outruns_though_its_rebase_run_ended_blocked(self):
        # Arrange
        self._block_the_last_rebase_run()
        self.machine.answers[MILESTONE_BRANCH_DESCENT] = ProcessAnswer()
        errors = io.StringIO()

        # Act
        with contextlib.redirect_stderr(errors):
            COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertNotIn("brigade tick: the rebase of integration/tides is blocked", errors.getvalue())


OUTPUTS_OF_A_LAUNCH_STOPPED_ON_A_CONFLICT = {
    **MACHINE_ANSWERS,
    ("git", "merge-base", "--is-ancestor", "integration/M4", "feature/T7-tide-table"): ProcessAnswer(exit_code=1),
    ("git", "merge-base", "--is-ancestor", "feature/T7-tide-table", "integration/M4"): ProcessAnswer(exit_code=1),
    ("git", "rebase", "--fork-point", "integration/M4"): ProcessAnswer(
        exit_code=1, stderr="CONFLICT (content): Merge conflict in src/tides.py"
    ),
    ("git", "rev-parse", "--quiet", "--verify", "REBASE_HEAD"): ProcessAnswer(stdout="f02da32\n"),
    ("git", "rebase", "--abort"): ProcessAnswer(),
    ("git", "rev-parse", "HEAD"): ProcessAnswer(stdout="4c0e214\n"),
    ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "feature/T7-tide-table^{commit}"): ProcessAnswer(
        stdout="4c0e214\n"
    ),
}
T7_HEAD = "4c0e214"
GREEN_PULL_REQUEST_AT_THE_T7_HEAD = {**GREEN_PULL_REQUEST, "head": "4c0e214"}
PASSED = 0
FAILED = 1


def write_commit_checks(root: Path, commit: str, exit_code: int) -> None:
    record = root / "state" / "commit-checks" / "tidepool" / f"{commit}.json"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "project": "tidepool",
                "commit": commit,
                "checks": [{"command": "make test", "exit_code": exit_code}],
            }
        ),
        encoding="utf-8",
    )


OUTPUTS_OF_A_LAUNCH_FROM_THE_FORGE_STOPPED_ON_A_CONFLICT = {
    **OUTPUTS_OF_A_LAUNCH_STOPPED_ON_A_CONFLICT,
    ("git", "merge-base", "--is-ancestor", "origin/integration/M4", "feature/T7-tide-table"): ProcessAnswer(
        exit_code=1
    ),
    ("git", "rebase", "--fork-point", "origin/integration/M4"): ProcessAnswer(
        exit_code=1, stderr="CONFLICT (content): Merge conflict in src/tides.py"
    ),
}

REBASE_RUN_OF_T7 = "20261018T100000Z-5e6f70"
T7_RUNNING = {
    "schema_version": 1,
    "ts": "2026-10-18T10:00:00Z",
    "event": "task.state",
    "wave": "tidepool_w16",
    "task": "T7",
    "state": "running",
}
REBASE_OF_T7_DONE = {
    **create_run_result(REBASE_RUN_OF_T7, "done", "2026-10-18T10:30:00Z"),
    "slot": "rebase",
    "wave": "tidepool_w16",
    "task": "T7",
}


class TickLaunchingATaskWhoseChecksPassedAndWhoseBranchConflictsWithTheWaveBranchTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        self.repository = self.root / "tidepool"
        self.worktree = self.repository / ".brigade" / "worktrees" / "T7"
        self.worktree.mkdir(parents=True)
        self.spawn = SpawnRecorderDouble()
        write_ledger(self.root, [CUT_OF_M4_ON_THE_WAVE_BRANCH, WAVE_STARTED, T7_RUNNING, REBASE_OF_T7_DONE])
        write_run(
            self.root / "state",
            {
                **create_run_record(REBASE_RUN_OF_T7, "tidepool_w16", "T7"),
                "slot": "rebase",
                "project": "tidepool",
                "cwd": str(self.worktree),
                "worktree": str(self.worktree),
            },
            REBASE_OF_T7_DONE,
        )
        write_commit_checks(self.root, WAVE_HEAD, PASSED)
        self.runtime = self._create_runtime()

    def _create_runtime(self, forge_name: str = "github", red_branch: str | None = None) -> Runtime:
        corpus = {
            "STUDY": PAUSED_BUILT_IN_STUDIES,
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"), ("FORGE", forge_name))},
            "TASK": {"T7": TASK_TO_DELIVER},
        }
        forge = RedBranchForgeDouble(RebasingForgeDouble([GREEN_PULL_REQUEST_AT_THE_T7_HEAD]), red_branch)
        return create_test_runtime(
            create_test_paths(self.root),
            run_process=ScriptedProcessRunner(
                OUTPUTS_OF_A_LAUNCH_FROM_THE_FORGE_STOPPED_ON_A_CONFLICT, fallback=create_corpus_double(corpus)
            ).run,
            spawn_process=self.spawn.spawn,
            resolve_plugin=_serve_the_forge_double_as(
                forge_name,
                _resolve_the_collectors_beside(create_plugin_resolution(STEP_COUNTING_PROBE, forge), self.root),
            ),
        )

    def test_should_hold_the_launch_on_the_check_runs_the_forge_of_the_project_lists(self):
        # Arrange
        (self.root / "state" / "commit-checks" / "tidepool" / f"{WAVE_HEAD}.json").unlink()
        runtime = self._create_runtime(forge_name=FORGE_OF_NO_GITHUB, red_branch="integration/M4")
        errors = io.StringIO()

        # Act
        with contextlib.redirect_stderr(errors):
            COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertIn(
            f"brigade tick: @TASK.T7 waits: integration/M4 is red at {WAVE_HEAD}, `ci / tests` failed\n",
            errors.getvalue(),
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


class TickLaunchingATaskWithoutAPullRequestWhoseBranchConflictsWithTheWaveBranchTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        self.repository = self.root / "tidepool"
        self.worktree = self.repository / ".brigade" / "worktrees" / "T7"
        self.worktree.mkdir(parents=True)
        self.spawn = SpawnRecorderDouble()
        write_ledger(self.root, [CUT_OF_M4_ON_THE_WAVE_BRANCH, WAVE_STARTED])
        write_commit_checks(self.root, T7_HEAD, PASSED)
        write_commit_checks(self.root, WAVE_HEAD, PASSED)
        corpus = {
            "STUDY": PAUSED_BUILT_IN_STUDIES,
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"))},
            "TASK": {"T7": TASK_TO_DELIVER},
        }
        self.machine = ScriptedProcessRunner(
            OUTPUTS_OF_A_LAUNCH_STOPPED_ON_A_CONFLICT, fallback=create_corpus_double(corpus)
        )
        self.runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=self.machine.run,
            spawn_process=self.spawn.spawn,
            resolve_plugin=create_plugin_resolution(STEP_COUNTING_PROBE, RebasingForgeDouble([None])),
        )

    def test_should_rebase_the_branch_onto_the_wave_branch(self):
        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(
            select_argvs_opening_on(self.machine.argvs, GIT_REBASE),
            [("git", "rebase", "--fork-point", "integration/M4"), ("git", "rebase", "--abort")],
        )

    def test_should_launch_the_rebase_slot_with_the_task_and_its_base_and_no_pull_request(self):
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


def create_the_worktree_at_its_addition(run_process):
    def run(request):
        if request.argv[:3] == ("git", "worktree", "add"):
            Path(request.argv[-2]).mkdir(parents=True, exist_ok=True)
        return run_process(request)

    return run


class TickHoldingTheLaunchOfAGreenTaskOffARedWaveBranchTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        self.repository = self.root / "tidepool"
        (self.repository / ".brigade" / "worktrees" / "T7").mkdir(parents=True)
        self.spawn = SpawnRecorderDouble()
        write_ledger(self.root, [CUT_OF_M4_ON_THE_WAVE_BRANCH, WAVE_STARTED])
        write_commit_checks(self.root, T7_HEAD, PASSED)
        write_commit_checks(self.root, WAVE_HEAD, FAILED)
        corpus = {
            "STUDY": PAUSED_BUILT_IN_STUDIES,
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"))},
            "TASK": {"T7": TASK_TO_DELIVER},
        }
        self.machine = ScriptedProcessRunner(
            OUTPUTS_OF_A_LAUNCH_STOPPED_ON_A_CONFLICT, fallback=create_corpus_double(corpus)
        )
        self.runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=create_the_worktree_at_its_addition(self.machine.run),
            spawn_process=self.spawn.spawn,
            resolve_plugin=create_plugin_resolution(STEP_COUNTING_PROBE, RebasingForgeDouble([None])),
        )

    def test_should_launch_one_run_repairing_the_red_wave_branch_in_its_worktree_and_no_build(self):
        # Act
        with contextlib.redirect_stderr(io.StringIO()):
            COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(
            self.spawn.argvs,
            [
                (
                    "run",
                    "rebase-on-base",
                    "branch=integration/M4",
                    f"head={WAVE_HEAD}",
                    "--slot",
                    "rebase",
                    "--cwd",
                    str(self.repository / ".brigade" / "worktrees" / "integration-M4"),
                    "--project",
                    "tidepool",
                    "--run-id",
                    ANY,
                )
            ],
        )

    def test_should_launch_no_second_repair_while_the_first_lives(self):
        # Arrange
        live_repair = {
            **create_run_record(FIRST_RUN, None, None),
            "slot": "rebase",
            "arguments": {"branch": "integration/M4", "head": WAVE_HEAD},
            "project": "tidepool",
            "cwd": str(self.repository / ".brigade" / "worktrees" / "integration-M4"),
            "worktree": str(self.repository / ".brigade" / "worktrees" / "integration-M4"),
        }
        record_run_pid(write_run(self.root / "state", live_repair, None), os.getpid())

        # Act
        with contextlib.redirect_stderr(io.StringIO()):
            COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(self.spawn.argvs, [])

    def test_should_name_the_question_of_the_repair_ended_blocked_at_each_tick_and_launch_no_other(self):
        # Arrange
        blocked_repair = {
            **create_run_record(FIRST_RUN, None, None),
            "slot": "rebase",
            "arguments": {"branch": "integration/M4", "head": WAVE_HEAD},
            "project": "tidepool",
            "cwd": str(self.repository / ".brigade" / "worktrees" / "integration-M4"),
            "worktree": str(self.repository / ".brigade" / "worktrees" / "integration-M4"),
        }
        blocked = {
            **create_run_result(FIRST_RUN, "blocked", "2026-10-18T10:30:00Z"),
            "message": "Drop the flaky tide test or fix its clock?\nbrigade-end: blocked",
        }
        write_run(self.root / "state", blocked_repair, blocked)
        errors = io.StringIO()

        # Act
        with contextlib.redirect_stderr(errors):
            COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(self.spawn.argvs, [])
        self.assertEqual(
            errors.getvalue().splitlines()[-1],
            "brigade tick: the repair of integration/M4 is blocked: Drop the flaky tide test or fix its clock?",
        )

    def test_should_name_the_red_wave_branch_its_commit_and_the_command_that_failed_on_stderr(self):
        # Arrange
        errors = io.StringIO()

        # Act
        with contextlib.redirect_stderr(errors):
            COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertIn(
            "brigade tick: @TASK.T7 waits: integration/M4 is red at 8885daa, `make test` failed\n", errors.getvalue()
        )

    def test_should_record_no_state_for_the_task(self):
        # Act
        with contextlib.redirect_stderr(io.StringIO()):
            COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        events = (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(json.loads(events[-1])["event"], "wave.started")

    def test_should_launch_the_held_task_at_the_tick_that_reads_its_base_green(self):
        # Arrange
        with contextlib.redirect_stderr(io.StringIO()):
            COMMAND.run(Namespace(mode="once"), self.runtime)
        write_commit_checks(self.root, WAVE_HEAD, PASSED)

        # Act
        with contextlib.redirect_stderr(io.StringIO()):
            COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(
            self.spawn.argvs[-1],
            (
                "run",
                "rebase-on-base",
                "task=@TASK.T7",
                "base=integration/M4",
                "--slot",
                "rebase",
                "--cwd",
                str(self.repository / ".brigade" / "worktrees" / "T7"),
                "--project",
                "tidepool",
                "--wave",
                "tidepool_w16",
                "--task",
                "T7",
                "--run-id",
                ANY,
            ),
        )

    def test_should_check_an_unproven_base_once_and_hold_the_launch_on_its_record_at_the_next_tick(self):
        # Arrange
        (self.root / "state" / "commit-checks" / "tidepool" / f"{WAVE_HEAD}.json").unlink()
        checkout = str(self.root / "state" / "head-checks" / "tidepool" / WAVE_HEAD)
        self.machine.answers[("awawa", "lint", "--strict", ".")] = ProcessAnswer(exit_code=1)
        with contextlib.redirect_stderr(io.StringIO()):
            COMMAND.run(Namespace(mode="once"), self.runtime)

        # Act
        with contextlib.redirect_stderr(io.StringIO()):
            COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(
            self.machine.argvs.count(("git", "worktree", "add", "--quiet", "--detach", checkout, WAVE_HEAD)), 1
        )

    def test_should_name_the_red_wave_branch_holding_the_launch_in_the_plan_of_a_dry_run(self):
        # Act
        document = COMMAND.run(Namespace(mode="dry-run"), self.runtime)

        # Assert
        self.assertIn(
            {
                "project": "tidepool",
                "wave": "tidepool_w16",
                "branch": "integration/M4",
                "task": "T7",
                "task_branch": "feature/T7-tide-table",
                "pull_request_checks": None,
                "waits": "integration/M4 is red at 8885daa, `make test` failed",
            },
            document["plan"],
        )

    def test_should_run_no_command_of_the_project_on_a_dry_run(self):
        # Arrange
        (self.root / "state" / "commit-checks" / "tidepool" / f"{WAVE_HEAD}.json").unlink()

        # Act
        document = COMMAND.run(Namespace(mode="dry-run"), self.runtime)

        # Assert
        self.assertIn(
            {
                "project": "tidepool",
                "wave": "tidepool_w16",
                "branch": "integration/M4",
                "task": "T7",
                "task_branch": "feature/T7-tide-table",
                "pull_request_checks": None,
            },
            document["plan"],
        )


IS_T7_ON_THE_WAVE_BRANCH = ("git", "merge-base", "--is-ancestor", "integration/M4", "feature/T7-tide-table")
BRANCH_OFF_THE_WAVE_BRANCH = ProcessAnswer(exit_code=1)
BRANCH_DESCENDING_FROM_THE_WAVE_BRANCH = ProcessAnswer()
SHOW_T7 = ("awawa", "show", "@TASK.T7", "--json")
T7_RULED_ON_THE_WAVE_BRANCH = ProcessAnswer(
    stdout=r'{"fields": [{"name": "TITLE", "atoms": ["\"Tide table\""]}, {"name": "TYPE", "atoms": ["feat"]},'
    r' {"name": "MILESTONE", "atoms": ["@MILESTONE.M4"]}, {"name": "STATUS", "atoms": ["todo"]},'
    r' {"name": "SPEC", "atoms": ["\"the tides follow the moon\""]}]}'
)
T7_AS_IN_THE_WORKTREE = ProcessAnswer(
    stdout=r'{"fields": [{"name": "TITLE", "atoms": ["\"Tide table\""]}, {"name": "TYPE", "atoms": ["feat"]},'
    r' {"name": "MILESTONE", "atoms": ["@MILESTONE.M4"]}, {"name": "STATUS", "atoms": ["todo"]}]}'
)


class TickBriefingATaskOnTheTaskAsItReadsOnTheWaveBranchTest(unittest.TestCase):
    def _create_runtime(self, root: Path, descent: ProcessAnswer, on_the_wave_branch: ProcessAnswer) -> Runtime:
        write_operational_corpus(root)
        (root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        repository = root / "tidepool"
        (repository / ".brigade" / "worktrees" / "T7").mkdir(parents=True)
        write_ledger(root, [CUT_OF_M4_ON_THE_WAVE_BRANCH, WAVE_STARTED])
        write_commit_checks(root, T7_HEAD, FAILED)
        corpus = {
            "STUDY": PAUSED_BUILT_IN_STUDIES,
            "PROJECT": {"tidepool": (("PATH", str(repository)), ("MAIN", "main"))},
            "TASK": {"T7": TASK_TO_DELIVER},
        }
        answers = {
            **MACHINE_ANSWERS,
            ("git", "rev-parse", "HEAD"): ProcessAnswer(stdout=f"{T7_HEAD}\n"),
            IS_T7_ON_THE_WAVE_BRANCH: descent,
            ("git", "merge-base", "--is-ancestor", "feature/T7-tide-table", "integration/M4"): ProcessAnswer(
                exit_code=1
            ),
            (*SHOW_T7, str(root / "cache" / "refs" / "tidepool" / WAVE_HEAD)): on_the_wave_branch,
        }
        return create_test_runtime(
            create_test_paths(root),
            run_process=ScriptedProcessRunner(answers, fallback=create_corpus_double(corpus)).run,
            spawn_process=SpawnRecorderDouble().spawn,
            resolve_plugin=create_plugin_resolution(STEP_COUNTING_PROBE, RebasingForgeDouble([None])),
        )

    def test_should_give_the_build_of_a_red_branch_off_the_wave_branch_the_task_as_it_reads_on_the_wave_branch(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        runtime = self._create_runtime(root, BRANCH_OFF_THE_WAVE_BRANCH, T7_RULED_ON_THE_WAVE_BRANCH)

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            (root / "state" / "briefs" / "tidepool_w16-T7.md").read_text(encoding="utf-8"),
            "Deliver @TASK.T7 of @PROJECT.tidepool, in the wave tidepool_w16.\n"
            "\n"
            "- Base branch: integration/M4.\n"
            f"- Worktree: {root / 'tidepool' / '.brigade' / 'worktrees' / 'T7'}, on the branch feature/T7-tide-table,"
            " left as it stands, off the head of integration/M4: its head failed `make test`;"
            " repair those failures first, and do not rebase the branch.\n"
            "\n"
            "@TASK.T7 reads differently on integration/M4 than in the corpus of the worktree;"
            " that reading is more recent and prevails:\n"
            "\n"
            "```\n"
            "TASK T7\n"
            "\tTITLE Tide table\n"
            "\tTYPE feat\n"
            "\tMILESTONE @MILESTONE.M4\n"
            "\tSTATUS todo\n"
            "\tSPEC the tides follow the moon\n"
            "```\n",
        )

    def test_should_leave_the_brief_as_it_was_when_the_task_reads_the_same_on_the_wave_branch(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        runtime = self._create_runtime(root, BRANCH_OFF_THE_WAVE_BRANCH, T7_AS_IN_THE_WORKTREE)

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            (root / "state" / "briefs" / "tidepool_w16-T7.md").read_text(encoding="utf-8"),
            "Deliver @TASK.T7 of @PROJECT.tidepool, in the wave tidepool_w16.\n"
            "\n"
            "- Base branch: integration/M4.\n"
            f"- Worktree: {root / 'tidepool' / '.brigade' / 'worktrees' / 'T7'}, on the branch feature/T7-tide-table,"
            " left as it stands, off the head of integration/M4: its head failed `make test`;"
            " repair those failures first, and do not rebase the branch.\n",
        )

    def test_should_read_no_task_on_the_wave_branch_for_a_branch_descending_from_it(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        runtime = self._create_runtime(root, BRANCH_DESCENDING_FROM_THE_WAVE_BRANCH, T7_RULED_ON_THE_WAVE_BRANCH)

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            (root / "state" / "briefs" / "tidepool_w16-T7.md").read_text(encoding="utf-8"),
            "Deliver @TASK.T7 of @PROJECT.tidepool, in the wave tidepool_w16.\n"
            "\n"
            "- Base branch: integration/M4.\n"
            f"- Worktree: {root / 'tidepool' / '.brigade' / 'worktrees' / 'T7'}, on the branch feature/T7-tide-table,"
            " cut from the head of integration/M4.\n",
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
                {"STUDY": {"health": HEALTH_STUDY, **PAUSED_BUILT_IN_STUDIES}}, MACHINE_OUTPUTS
            ),
            spawn_process=spawn.spawn,
            resolve_plugin=create_plugin_resolution(STEP_COUNTING_PROBE),
        )

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(spawn.argvs, [("study", "run", "health", "--run-id", ANY)])

    def test_should_launch_the_built_in_studies_on_a_machine_that_never_ran_them(self):
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
        self.assertEqual(
            spawn.argvs,
            [("study", "run", "mine_transcripts", "--run-id", ANY), ("study", "run", "triage", "--run-id", ANY)],
        )

    def test_should_launch_the_built_in_scans_of_a_registered_project_on_a_machine_that_never_ran_them(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        spawn = SpawnRecorderDouble()
        oak = (("PATH", str(root / "oak")), ("MAIN", "main"), ("FORGE", "none"), ("STATUS", "paused"))
        runtime = create_test_runtime(
            create_test_paths(root),
            run_process=create_machine_double(
                {"PROJECT": {"oak": oak}, "STUDY": {"triage": PAUSED_TRIAGE, "mine_transcripts": PAUSED_TRIAGE}},
                MACHINE_OUTPUTS,
            ),
            spawn_process=spawn.spawn,
            resolve_plugin=create_plugin_resolution(STEP_COUNTING_PROBE),
        )

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            spawn.argvs,
            [
                ("study", "run", "corpus_fmt_oak", "--run-id", ANY),
                ("study", "run", "corpus_lint_oak", "--run-id", ANY),
                ("study", "run", "stale_branches_oak", "--run-id", ANY),
                ("study", "run", "worktrees_oak", "--run-id", ANY),
            ],
        )


BEHIND_PULL_REQUEST = {**GREEN_PULL_REQUEST, "behind": True}
REBASED_HEAD = "9a9a9a9"
REBASED_PULL_REQUEST = {**OPEN_PULL_REQUEST, "head": REBASED_HEAD, "checks": [{"name": "ci", "verdict": "pending"}]}
REBASE_ONTO_THE_WAVE_BRANCH = ("git", "rebase", "--fork-point", "origin/integration/M4")
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
OUTPUTS_OF_A_REBASE_OF_A_WORKTREE_HOLDING_CHANGES = {
    **REBASE_OUTPUTS,
    ("git", "status", "--porcelain", "--untracked-files=no"): ProcessAnswer(stdout=" M src/tides.py\n"),
    ("git", "diff", "--cached", "--quiet"): ProcessAnswer(exit_code=STAGED_CHANGES_FOUND),
    GIT_COMMIT: ProcessAnswer(),
}
LEDGER_OF_A_TASK_IN_VERIFYING = [
    CUT_OF_M4_ON_THE_WAVE_BRANCH,
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


FORGE_OF_NO_GITHUB = "forgejo"


def _red_check_run_at(head: str) -> dict:
    return {
        "pull_request": None,
        "branch": "integration/M4",
        "head": head,
        "name": "ci / tests",
        "conclusion": "failure",
        "link": "https://forge.example/tidepool/runs/7",
    }


class RedBranchForgeDouble:
    def __init__(self, forge: object, branch: str):
        self.forge = forge
        self.branch = branch

    def __getattr__(self, name: str):
        return getattr(self.forge, name)

    def list_check_runs(self, request: dict, runtime) -> dict:
        if request["branch"] == self.branch:
            return {"schema_version": 1, "check_runs": [_red_check_run_at(WAVE_HEAD)]}
        return self.forge.list_check_runs(request, runtime)

    def read_job_steps(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "steps": None}


def _serve_the_forge_double_as(forge_name: str, resolve_plugin):
    def resolve(kind: str, name: str, **options):
        if kind != "forge":
            return resolve_plugin(kind, name, **options)
        if name != forge_name:
            raise AssertionError(f"the command resolved the forge plugin {name}")
        return resolve_plugin(kind, "github", **options)

    return resolve


class RebasingForgeDouble(ForgeWithNothingToCollectDouble):
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
        write_commit_checks(self.root, WAVE_HEAD, PASSED)

    def _create_runtime(
        self, outputs: dict, found: list[dict], forge_name: str = "github", red_branch: str | None = None
    ) -> Runtime:
        corpus = {
            "STUDY": PAUSED_BUILT_IN_STUDIES,
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"), ("FORGE", forge_name))},
            "TASK": {"T7": TASK_DELIVERED, "T8": TASK_DELIVERED},
        }
        self.machine = ScriptedProcessRunner(outputs, fallback=create_corpus_double(corpus))
        forge = RebasingForgeDouble(found)
        return create_test_runtime(
            create_test_paths(self.root),
            run_process=create_the_worktree_at_its_addition(self._observe_the_lock(self.machine.run)),
            spawn_process=self.spawn.spawn,
            resolve_plugin=_serve_the_forge_double_as(
                forge_name,
                _resolve_the_collectors_beside(
                    create_plugin_resolution(STEP_COUNTING_PROBE, RedBranchForgeDouble(forge, red_branch)), self.root
                ),
            ),
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

    def test_should_rebase_nothing_while_the_head_of_the_wave_branch_is_red(self):
        # Arrange
        write_ledger(self.root, LEDGER_OF_A_TASK_IN_VERIFYING)
        write_commit_checks(self.root, WAVE_HEAD, FAILED)
        runtime = self._create_runtime(REBASE_OUTPUTS, [BEHIND_PULL_REQUEST])

        # Act
        with contextlib.redirect_stderr(io.StringIO()):
            COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(select_argvs_opening_on(self.machine.argvs, GIT_REBASE, GIT_PUSH), [])

    def test_should_name_the_red_wave_branch_holding_the_catch_up_on_stderr(self):
        # Arrange
        write_ledger(self.root, LEDGER_OF_A_TASK_IN_VERIFYING)
        write_commit_checks(self.root, WAVE_HEAD, FAILED)
        runtime = self._create_runtime(REBASE_OUTPUTS, [BEHIND_PULL_REQUEST])
        errors = io.StringIO()

        # Act
        with contextlib.redirect_stderr(errors):
            COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertIn(
            "brigade tick: the catch-up of @TASK.T7 waits: integration/M4 is red at 8885daa, `make test` failed\n",
            errors.getvalue(),
        )

    def test_should_hold_the_catch_up_on_the_check_runs_the_forge_of_the_project_lists(self):
        # Arrange
        write_ledger(self.root, LEDGER_OF_A_TASK_IN_VERIFYING)
        (self.root / "state" / "commit-checks" / "tidepool" / f"{WAVE_HEAD}.json").unlink()
        runtime = self._create_runtime(
            REBASE_OUTPUTS, [BEHIND_PULL_REQUEST], forge_name=FORGE_OF_NO_GITHUB, red_branch="integration/M4"
        )
        errors = io.StringIO()

        # Act
        with contextlib.redirect_stderr(errors):
            COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertIn(
            "brigade tick: the catch-up of @TASK.T7 waits: integration/M4 is red at 8885daa, `ci / tests` failed\n",
            errors.getvalue(),
        )

    def test_should_name_in_the_dry_run_the_check_runs_the_forge_of_the_project_lists_holding_the_catch_up(self):
        # Arrange
        write_ledger(self.root, LEDGER_OF_A_TASK_IN_VERIFYING)
        (self.root / "state" / "commit-checks" / "tidepool" / f"{WAVE_HEAD}.json").unlink()
        runtime = self._create_runtime(
            REBASE_OUTPUTS, [BEHIND_PULL_REQUEST], forge_name=FORGE_OF_NO_GITHUB, red_branch="integration/M4"
        )

        # Act
        document = COMMAND.run(Namespace(mode="dry-run"), runtime)

        # Assert
        self.assertIn(
            {
                "project": "tidepool",
                "wave": "tidepool_w16",
                "branch": "integration/M4",
                "task": "T7",
                "task_branch": "feature/T7-tide-table",
                "pr": 42,
                "worktree": str(self.worktree),
                "head": WAVE_HEAD,
                "holds_uncommitted_changes": False,
                "waits": f"integration/M4 is red at {WAVE_HEAD}, `ci / tests` failed",
            },
            document["plan"],
        )

    def test_should_launch_one_run_repairing_the_red_wave_branch_holding_the_catch_up(self):
        # Arrange
        write_ledger(self.root, LEDGER_OF_A_TASK_IN_VERIFYING)
        write_commit_checks(self.root, WAVE_HEAD, FAILED)
        runtime = self._create_runtime(REBASE_OUTPUTS, [BEHIND_PULL_REQUEST])

        # Act
        with contextlib.redirect_stderr(io.StringIO()):
            COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self.spawn.argvs,
            [
                (
                    "run",
                    "rebase-on-base",
                    "branch=integration/M4",
                    f"head={WAVE_HEAD}",
                    "--slot",
                    "rebase",
                    "--cwd",
                    ANY,
                    "--project",
                    "tidepool",
                    "--run-id",
                    ANY,
                )
            ],
        )

    def test_should_launch_one_run_repairing_the_red_wave_branch_two_catch_ups_wait_on(self):
        # Arrange
        write_ledger(
            self.root,
            [
                CUT_OF_M4_ON_THE_WAVE_BRANCH,
                {**WAVE_STARTED, "tasks": ["T7", "T8"]},
                TASK_PR_OPENED,
                {**TASK_PR_OPENED, "task": "T8", "branch": "feature/T8-tide-chart", "pr": 43},
                TASK_PREFLIGHTED_AT_THE_HEAD,
                {**TASK_PREFLIGHTED_AT_THE_HEAD, "task": "T8", "pr": 43},
                _record_task_state("verifying"),
                {**_record_task_state("verifying"), "task": "T8"},
            ],
        )
        write_commit_checks(self.root, WAVE_HEAD, FAILED)
        (self.repository / ".brigade" / "worktrees" / "T8").mkdir(parents=True)
        runtime = self._create_runtime(REBASE_OUTPUTS, [BEHIND_PULL_REQUEST])
        errors = io.StringIO()

        # Act
        with contextlib.redirect_stderr(errors):
            COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self.spawn.argvs,
            [
                (
                    "run",
                    "rebase-on-base",
                    "branch=integration/M4",
                    f"head={WAVE_HEAD}",
                    "--slot",
                    "rebase",
                    "--cwd",
                    ANY,
                    "--project",
                    "tidepool",
                    "--run-id",
                    ANY,
                )
            ],
        )
        self.assertIn(
            "brigade tick: the catch-up of @TASK.T8 waits: integration/M4 is red at 8885daa, `make test` failed\n",
            errors.getvalue(),
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
                (
                    "git",
                    "push",
                    "--quiet",
                    "--force-with-lease=feature/T7-tide-table:8885daa",
                    "origin",
                    "HEAD:feature/T7-tide-table",
                ),
            ],
        )

    def test_should_stage_nothing_in_a_worktree_holding_no_uncommitted_change_before_rebasing_it(self):
        # Arrange
        write_ledger(self.root, LEDGER_OF_A_TASK_IN_VERIFYING)
        runtime = self._create_runtime(REBASE_OUTPUTS, [BEHIND_PULL_REQUEST, REBASED_PULL_REQUEST])

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            select_argvs_opening_on(self.machine.argvs, GIT_ADD, GIT_COMMIT, GIT_REBASE),
            [REBASE_ONTO_THE_WAVE_BRANCH],
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
                CUT_OF_M4_ON_THE_WAVE_BRANCH,
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
                    "branch": "feature/T7-tide-table",
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
        self.assertEqual(
            self.environments_of_the_fetch,
            [ENVIRONMENT_OF_THE_CLI_ACCOUNT, ENVIRONMENT_OF_THE_CLI_ACCOUNT, ENVIRONMENT_OF_THE_CLI_ACCOUNT],
        )

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
                CUT_OF_M4_ON_THE_WAVE_BRANCH,
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
                    "branch": "feature/T7-tide-table",
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

    def test_should_launch_the_rebase_slot_on_a_conflict_whatever_the_repair_rounds_spent(self):
        # Arrange
        write_ledger(self.root, LEDGER_OF_A_TASK_PAST_ITS_ROUNDS)
        runtime = self._create_runtime(OUTPUTS_OF_A_REBASE_STOPPED_ON_A_CONFLICT, [BEHIND_PULL_REQUEST])

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
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

    def test_should_commit_the_uncommitted_changes_of_a_task_past_its_rounds_before_rebasing_it(self):
        # Arrange
        write_ledger(self.root, LEDGER_OF_A_TASK_PAST_ITS_ROUNDS)
        runtime = self._create_runtime(
            OUTPUTS_OF_A_REBASE_OF_A_WORKTREE_HOLDING_CHANGES, [BEHIND_PULL_REQUEST, REBASED_PULL_REQUEST]
        )

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            select_argvs_opening_on(self.machine.argvs, GIT_ADD, GIT_COMMIT, GIT_REBASE, GIT_PUSH),
            [
                ("git", "add", "--", "."),
                (
                    "git",
                    "commit",
                    "--quiet",
                    "-m",
                    "chore(tick): keep the changes of @TASK.T7 left uncommitted before its rebase",
                ),
                REBASE_ONTO_THE_WAVE_BRANCH,
                (
                    "git",
                    "push",
                    "--quiet",
                    "--force-with-lease=feature/T7-tide-table:8885daa",
                    "origin",
                    "HEAD:feature/T7-tide-table",
                ),
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
            "list_check_runs": lambda request: {"schema_version": 1, "check_runs": []},
            "list_review_threads": lambda request: {"schema_version": 1, "threads": []},
            "list_pull_requests": lambda request: {"schema_version": 1, "pull_requests": []},
        }
    )


class TickReadingAsTheForgeAccountOfTheCliTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        self.repository = self.root / "tidepool"

    def _create_runtime(self, binding: str, forge: ForgeDouble, project_forge: str) -> Runtime:
        (self.root / "config" / "config.toml").write_text(
            CLIENT_AND_DOCUMENT_CONFIGURATION + ONE_FORGE_ATTEMPT + binding, encoding="utf-8"
        )
        corpus = {
            "STUDY": PAUSED_BUILT_IN_STUDIES,
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"), ("FORGE", project_forge))},
            "TASK": {"T7": TASK_TO_DELIVER},
        }
        return create_test_runtime(
            create_test_paths(self.root),
            run_process=create_machine_double(corpus, MACHINE_OUTPUTS),
            resolve_plugin=_resolve_the_collectors_beside(
                create_plugin_resolution(STEP_COUNTING_PROBE, forge), self.root
            ),
        )

    def test_should_read_the_pull_request_of_a_running_task_as_the_login_of_the_key_cli(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("running")])
        forge = create_forge_of_the_cli(OPEN_PULL_REQUEST, ENVIRONMENT_OF_THE_CLI_ACCOUNT)
        runtime = self._create_runtime(CLI_BOUND_TO_A_FORGE_ACCOUNT, forge, "github")

        # Act
        COMMAND.run(Namespace(mode="dry-run"), runtime)

        # Assert
        self.assertEqual(
            forge.list_requests("find_pull_request"),
            [
                {
                    "schema_version": 1,
                    "repository": str(self.repository),
                    "branch": "feature/T7-tide-table",
                    "environment": {"GH_TOKEN": "t0k3n"},
                },
                {
                    "schema_version": 1,
                    "repository": str(self.repository),
                    "branch": "integration/M4",
                    "environment": {"GH_TOKEN": "t0k3n"},
                },
            ],
        )

    def test_should_read_the_token_of_the_login_of_the_key_cli_once_per_tick(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("running")])
        forge = create_forge_of_the_cli(OPEN_PULL_REQUEST, ENVIRONMENT_OF_THE_CLI_ACCOUNT)
        runtime = self._create_runtime(CLI_BOUND_TO_A_FORGE_ACCOUNT, forge, "github")

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
        runtime = self._create_runtime(CLI_BOUND_TO_A_TOKENLESS_ACCOUNT, forge, "github")

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(mode="dry-run"), runtime)

        # Assert
        self.assertEqual(
            str(raised.exception), "gh printed no token for the login tidepool-tokenless, bound to cli, after 1 attempt"
        )

    def test_should_plan_the_wave_of_a_project_without_a_forge_with_no_token_for_the_login_of_the_key_cli(self):
        # Arrange
        write_ledger(self.root, [CUT_OF_M4_ON_THE_WAVE_BRANCH, WAVE_STARTED])
        forge = create_forge_of_the_cli(NO_PULL_REQUEST, NO_TOKEN)
        runtime = self._create_runtime(CLI_BOUND_TO_A_TOKENLESS_ACCOUNT, forge, "none")

        # Act
        document = COMMAND.run(Namespace(mode="dry-run"), runtime)

        # Assert
        self.assertEqual(
            document["plan"],
            [
                {
                    "project": "tidepool",
                    "wave": "tidepool_w16",
                    "branch": "integration/M4",
                    "task": "T7",
                    "task_branch": "feature/T7-tide-table",
                    "pull_request_checks": None,
                }
            ],
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
            "STUDY": PAUSED_BUILT_IN_STUDIES,
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
                "merge_commands": [],
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
            run_process=create_machine_double({"PROJECT": projects, "STUDY": PAUSED_BUILT_IN_STUDIES}, MACHINE_OUTPUTS),
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
MILESTONE_M4_REPORTED = {
    "schema_version": 1,
    "ts": "2026-10-19T09:00:00Z",
    "event": "milestone.reported",
    "project": "tidepool",
    "milestone": "M4",
    "run": ANY,
    "login": "tidepool-cli",
}
MILESTONE_PULL_REQUEST_MERGED = {**INTEGRATION_PULL_REQUEST_OPEN_INTO_MAIN, "number": 77, "state": "merged"}
TASK_OF_M4_TO_DELIVER = (("TITLE", "Tide table"), ("TYPE", "feat"), ("MILESTONE", "@MILESTONE.M4"), ("STATUS", "todo"))
TASK_OF_M4_DRAFTED = (("TITLE", "Tide table"), ("TYPE", "feat"), ("MILESTONE", "@MILESTONE.M4"), ("STATUS", "draft"))
TASK_OF_M5_DELIVERED = (
    ("TITLE", "Tide table"),
    ("TYPE", "feat"),
    ("MILESTONE", "@MILESTONE.M5"),
    ("STATUS", "implemented"),
    ("DELIVERED_BY", "42"),
)
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
NO_REQUEST: dict = {}
NO_OTHER_PROJECT = {}
MILESTONE_BRANCH_DELETED_FROM_THE_FORGE = CommandFailed(
    ("git", "fetch", "--quiet", "origin", MILESTONE_BRANCH), 128, "couldn't find remote ref integration/tides"
)
LS_REMOTE_OF_THE_MILESTONE_BRANCH = (
    "git",
    "ls-remote",
    "--quiet",
    "--exit-code",
    "--heads",
    "origin",
    f"refs/heads/{MILESTONE_BRANCH}",
)
MILESTONE_BRANCH_OFF_THE_FORGE = ProcessAnswer(exit_code=2)


class TickReportingAMilestoneTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        self.repository = self.root / "tidepool"
        self.forge = OpeningForgeDouble(NO_PULL_REQUEST_FROM_ANY_BRANCH)
        self.spawn = SpawnRecorderDouble()
        write_ledger(
            self.root,
            [WAVE_STARTED, _record_task_state("merged"), CUT_OF_M4, WAVE_REPORTED, WAVE_PR_OPENED, WAVE_CLOSED],
        )

    def _create_runtime(
        self,
        forge: OpeningForgeDouble,
        tasks: dict,
        answers: dict = MACHINE_ANSWERS,
        projects: dict = NO_OTHER_PROJECT,
        requests: dict = NO_REQUEST,
        forge_name: str = "github",
    ) -> Runtime:
        corpus = {
            "STUDY": PAUSED_BUILT_IN_STUDIES,
            "PROJECT": {
                "tidepool": (("PATH", str(self.repository)), ("MAIN", "main"), ("FORGE", forge_name)),
                **projects,
            },
            "TASK": tasks,
            "MILESTONE": {"M4": MILESTONE_M4, "M5": (("STATUS", "active"), ("TITLE", "Currents"))},
            "REQUEST": requests,
        }
        return create_test_runtime(
            create_test_paths(self.root),
            run_process=ScriptedProcessRunner(
                {**answers, ("git", "ls-remote"): ProcessAnswer(stdout="")}, fallback=create_corpus_double(corpus)
            ).run,
            spawn_process=self.spawn.spawn,
            resolve_plugin=_resolve_the_collectors_beside(
                create_plugin_resolution(STEP_COUNTING_PROBE, forge), self.root
            ),
        )

    def _read_reported_milestones(self) -> list[dict]:
        return select_reported_milestones(self._read_milestone_events())

    def _read_milestone_events(self) -> list[dict]:
        return select_milestone_events(
            map(json.loads, (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8").splitlines())
        )

    def test_should_report_the_milestone_once_its_last_wave_is_closed(self):
        # Act
        COMMAND.run(Namespace(mode="once"), self._create_runtime(self.forge, {"T7": TASK_DELIVERED}))

        # Assert
        self.assertEqual(self._read_reported_milestones(), [MILESTONE_M4_REPORTED])

    def test_should_record_the_report_with_the_run_it_detaches_and_the_login_of_the_cli(self):
        # Act
        COMMAND.run(Namespace(mode="once"), self._create_runtime(self.forge, {"T7": TASK_DELIVERED}))

        # Assert
        [[*_, reported_run]] = self.spawn.argvs
        self.assertEqual(self.spawn.argvs, [("study", "run", "milestone-report", "--run-id", reported_run)])
        self.assertEqual(
            self._read_milestone_events(),
            [
                CUT_OF_M4,
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "milestone.reported",
                    "project": "tidepool",
                    "milestone": "M4",
                    "run": reported_run,
                    "login": "tidepool-cli",
                },
            ],
        )

    def test_should_hand_the_report_run_the_branch_the_waves_and_the_tasks_of_the_milestone(self):
        # Act
        COMMAND.run(Namespace(mode="once"), self._create_runtime(self.forge, {"T7": TASK_DELIVERED}))

        # Assert
        [[*_, reported_run]] = self.spawn.argvs
        record = json.loads((self.root / "state" / "runs" / reported_run / "study.json").read_text(encoding="utf-8"))
        self.assertEqual(
            record["milestone"],
            {
                "project": "tidepool",
                "milestone": "M4",
                "branch": "integration/tides",
                "waves": ["tidepool_w16"],
                "tasks": ["T7"],
                "reads_pull_requests": True,
            },
        )

    def test_should_record_the_report_of_a_project_without_a_forge_with_no_login(self):
        # Arrange
        runtime = self._create_runtime(self.forge, {"T7": TASK_DELIVERED}, forge_name="none")

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(self._read_reported_milestones(), [{**MILESTONE_M4_REPORTED, "login": None}])

    def test_should_open_no_pull_request_of_the_milestone_before_its_report(self):
        # Act
        COMMAND.run(Namespace(mode="once"), self._create_runtime(self.forge, {"T7": TASK_DELIVERED}))

        # Assert
        self.assertEqual(self.forge.opened, [])

    def test_should_report_it_once_whatever_the_ticks_after_it(self):
        # Arrange
        runtime = self._create_runtime(self.forge, {"T7": TASK_DELIVERED})
        COMMAND.run(Namespace(mode="once"), runtime)

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(self._read_reported_milestones(), [MILESTONE_M4_REPORTED])

    def test_should_report_it_beside_the_pull_request_opened_for_another_milestone(self):
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
                self.assertEqual(self._read_reported_milestones(), [MILESTONE_M4_REPORTED])

    def test_should_report_it_beside_the_report_of_another_milestone(self):
        for case, reported_elsewhere in [
            ("another milestone of the project", {**MILESTONE_M4_REPORTED, "milestone": "M5", "run": "r1"}),
            (
                "the milestone of the same name of another project",
                {**MILESTONE_M4_REPORTED, "project": "reef", "run": "r1"},
            ),
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
                        reported_elsewhere,
                    ],
                )

                # Act
                COMMAND.run(Namespace(mode="once"), self._create_runtime(self.forge, {"T7": TASK_DELIVERED}))

                # Assert
                self.assertEqual(self._read_reported_milestones(), [reported_elsewhere, MILESTONE_M4_REPORTED])

    def test_should_report_none_on_the_closed_wave_of_another_project(self):
        # Arrange
        write_ledger(self.root, [CUT_OF_M4, WAVE_OF_ANOTHER_PROJECT_STARTED, WAVE_OF_ANOTHER_PROJECT_CLOSED])

        # Act
        COMMAND.run(Namespace(mode="once"), self._create_runtime(self.forge, {"T7": TASK_DELIVERED}))

        # Assert
        self.assertEqual(self._read_reported_milestones(), [])

    def test_should_report_it_beside_an_open_wave_of_no_task_of_the_milestone(self):
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
                self.assertEqual(self._read_reported_milestones(), [MILESTONE_M4_REPORTED])

    def test_should_skip_a_milestone_whose_branch_cannot_be_fetched(self):
        # Arrange
        answers = {
            **MACHINE_ANSWERS,
            ("git", "fetch", "--quiet", "origin", MILESTONE_BRANCH): MILESTONE_BRANCH_DELETED_FROM_THE_FORGE,
            LS_REMOTE_OF_THE_MILESTONE_BRANCH: MILESTONE_BRANCH_OFF_THE_FORGE,
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

    def test_should_report_it_beside_the_milestone_of_a_project_no_longer_registered(self):
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
        self.assertEqual(self._read_reported_milestones(), [MILESTONE_M4_REPORTED])

    def test_should_report_none_while_a_task_of_the_milestone_is_todo_at_its_branch(self):
        # Arrange
        runtime = self._create_runtime(self.forge, {"T7": TASK_DELIVERED, "T8": TASK_OF_M4_TO_DELIVER})

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(self._read_reported_milestones(), [])

    def test_should_report_none_while_a_task_of_the_milestone_is_draft_at_its_branch(self):
        # Arrange
        runtime = self._create_runtime(self.forge, {"T7": TASK_DELIVERED, "T8": TASK_OF_M4_DRAFTED})

        # Act
        with contextlib.redirect_stderr(io.StringIO()):
            COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(self._read_reported_milestones(), [])

    def test_should_name_the_open_tasks_holding_the_pull_request_of_the_milestone_in_the_dry_run(self):
        # Arrange
        runtime = self._create_runtime(
            self.forge, {"T7": TASK_DELIVERED, "T8": TASK_OF_M4_DRAFTED, "T9": TASK_OF_M4_TO_DELIVER}
        )

        # Act
        with contextlib.redirect_stderr(io.StringIO()):
            document = COMMAND.run(Namespace(mode="dry-run"), runtime)

        # Assert
        self.assertEqual(document["snapshot"]["milestones"][0]["open_tasks"], ["T8", "T9"])

    def test_should_report_none_while_no_closed_wave_holds_a_task_of_the_milestone(self):
        # Arrange
        runtime = self._create_runtime(self.forge, {"T7": TASK_OF_M5_DELIVERED})

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(self._read_reported_milestones(), [])

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

    def test_should_deliver_the_pattern_whose_request_the_closed_milestone_delivers(self):
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
        (self.root / "config" / "patterns.awawa").write_text(
            'PATTERN CartTimeouts\n\tTITLE "the cart tests fail on a timeout"\n\tSTATUS ratified\n\tACTION wave\n',
            encoding="utf-8",
        )
        request_from_the_pattern = {
            "tidepool_r1": (("PROJECT", "@PROJECT.tidepool"), ("MILESTONE", "M4"), ("FROM", "@PATTERN.CartTimeouts"))
        }
        forge = OpeningForgeDouble({MILESTONE_BRANCH: MILESTONE_PULL_REQUEST_MERGED})

        # Act
        COMMAND.run(
            Namespace(mode="once"),
            self._create_runtime(forge, {"T7": TASK_DELIVERED}, requests=request_from_the_pattern),
        )

        # Assert
        self.assertEqual(
            (self.root / "config" / "patterns.awawa").read_text(encoding="utf-8"),
            'PATTERN CartTimeouts\n\tTITLE "the cart tests fail on a timeout"\n\tSTATUS delivered\n\tACTION wave\n',
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
            LS_REMOTE_OF_THE_MILESTONE_BRANCH: MILESTONE_BRANCH_OFF_THE_FORGE,
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


SHA_OF_THE_PULL_REQUEST_HEAD = "a3e4d5f"
TASK_DELIVERED_TO_ITS_FIRST_WORDING = (*TASK_DELIVERED, ("SPEC", "the tide table lists the low tides"))
TASK_AMENDED_ON_THE_WAVE_BRANCH = (*TASK_TO_DELIVER, ("SPEC", "the tide table lists the low and the high tides"))
OUTPUTS_OF_AN_AMENDED_TASK = {
    **MACHINE_ANSWERS,
    ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "8885daa^{commit}"): ProcessAnswer(
        stdout=f"{SHA_OF_THE_PULL_REQUEST_HEAD}\n"
    ),
}


class TickRebuildingATaskAmendedOnItsWaveBranchTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        self.pull_request_tree = self.root / "cache" / "refs" / "tidepool" / SHA_OF_THE_PULL_REQUEST_HEAD
        self.pull_request_tree.mkdir(parents=True)
        self.repository = self.root / "tidepool"
        self.worktree = self.repository / ".brigade" / "worktrees" / "T7"
        self.worktree.mkdir(parents=True)
        self.spawn = SpawnRecorderDouble()
        corpus = {
            "STUDY": PAUSED_BUILT_IN_STUDIES,
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"), ("FORGE", "github"))},
            "TASK": {"T7": TASK_AMENDED_ON_THE_WAVE_BRANCH},
        }
        on_the_pull_request = {**corpus, "TASK": {"T7": TASK_DELIVERED_TO_ITS_FIRST_WORDING}}
        self.machine = ScriptedProcessRunner(
            OUTPUTS_OF_AN_AMENDED_TASK,
            fallback=lambda request: answer_from_corpus(
                on_the_pull_request if request.argv[-1] == str(self.pull_request_tree) else corpus, request
            ),
        )
        write_ledger(self.root, LEDGER_OF_A_TASK_IN_VERIFYING)
        self.runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=self.machine.run,
            spawn_process=self.spawn.spawn,
            resolve_plugin=_resolve_the_collectors_beside(
                create_plugin_resolution(STEP_COUNTING_PROBE, RebasingForgeDouble([BEHIND_PULL_REQUEST])), self.root
            ),
        )

    def test_should_launch_the_build_slot_on_the_worktree_of_the_task_and_rebase_nothing(self):
        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(select_argvs_opening_on(self.machine.argvs, GIT_REBASE, GIT_PUSH), [])
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
                    str(self.root / "state" / "briefs" / "tidepool_w16-T7-rebuild.md"),
                    "--wave",
                    "tidepool_w16",
                    "--task",
                    "T7",
                    "--run-id",
                    ANY,
                )
            ],
        )

    def test_should_record_the_task_in_fixing_for_the_amendment_of_its_entity(self):
        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(
            json.loads((self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8").splitlines()[5]),
            {
                "schema_version": 1,
                "ts": "2026-10-19T09:00:00Z",
                "event": "task.state",
                "wave": "tidepool_w16",
                "task": "T7",
                "state": "fixing",
                "reason": "the entity of the task amended on integration/M4",
            },
        )

    def test_should_print_the_rebuild_with_its_task_its_pull_request_and_its_base_on_a_dry_run(self):
        # Act
        document = COMMAND.run(Namespace(mode="dry-run"), self.runtime)

        # Assert
        self.assertEqual(
            document["plan"],
            [
                {
                    "project": "tidepool",
                    "wave": "tidepool_w16",
                    "base": "integration/M4",
                    "task": "T7",
                    "task_branch": "feature/T7-tide-table",
                    "pr": 42,
                    "worktree": str(self.worktree),
                    "reason": "the entity of the task amended on integration/M4",
                    "amendment": {
                        "on_pull_request": {
                            "name": "T7",
                            "fields": (
                                {"name": "TITLE", "value": "Tide table"},
                                {"name": "TYPE", "value": "feat"},
                                {"name": "MILESTONE", "value": "@MILESTONE.M4"},
                                {"name": "STATUS", "value": "implemented"},
                                {"name": "DELIVERED_BY", "value": "42"},
                                {"name": "SPEC", "value": "the tide table lists the low tides"},
                            ),
                        },
                        "on_wave": {
                            "name": "T7",
                            "fields": (
                                {"name": "TITLE", "value": "Tide table"},
                                {"name": "TYPE", "value": "feat"},
                                {"name": "MILESTONE", "value": "@MILESTONE.M4"},
                                {"name": "STATUS", "value": "todo"},
                                {"name": "SPEC", "value": "the tide table lists the low and the high tides"},
                            ),
                        },
                    },
                },
                {"project": "tidepool"},
                {"project": "tidepool"},
            ],
        )


WAVE_OF_TWO_TASKS_STARTED = {**WAVE_STARTED, "tasks": ["T7", "T8"]}


class TickBoundingItsReadsTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        self.repository = self.root / "tidepool"
        (self.repository / ".brigade" / "worktrees" / "T7").mkdir(parents=True)
        (self.repository / ".brigade" / "worktrees" / "T8").mkdir(parents=True)
        corpus = {
            "STUDY": {"triage": PAUSED_TRIAGE},
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"), ("FORGE", "github"))},
            "TASK": {"T7": TASK_TO_DELIVER, "T8": TASK_TO_DELIVER},
        }
        self.processes = ScriptedProcessRunner(MACHINE_ANSWERS, fallback=create_corpus_double(corpus))
        self.readings = LedgerReaderDouble()
        write_ledger(self.root, [WAVE_OF_TWO_TASKS_STARTED])

    def _create_runtime(self) -> Runtime:
        return create_test_runtime(
            create_test_paths(self.root),
            run_process=self.processes.run,
            spawn_process=SpawnRecorderDouble().spawn,
            resolve_plugin=_resolve_the_collectors_beside(
                create_plugin_resolution(STEP_COUNTING_PROBE, create_forge(NO_PULL_REQUEST, NO_DETAILS_ASKED)),
                self.root,
            ),
            read_ledger=self.readings.read,
        )

    def test_should_read_the_ledger_once_over_the_rounds_of_a_tick(self):
        # Arrange
        runtime = self._create_runtime()

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(self.readings.state_roots, [self.root / "state"])

    def test_should_read_the_references_of_each_task_once_over_the_rounds_of_a_tick(self):
        # Arrange
        runtime = self._create_runtime()

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        wave_tree = str(self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD)
        self.assertEqual(
            select_argvs_opening_on(self.processes.argvs, ("awawa", "refs")),
            [
                ("awawa", "refs", "@TASK.T7", "--json", wave_tree),
                ("awawa", "refs", "@TASK.T8", "--json", wave_tree),
            ],
        )


HEAD_OF_THE_WAVE_AFTER_THE_MERGE = "a1b2c3d"


class WaveBranchMovedByTheMergeDouble:
    def __init__(self, forge: MergingForgeDouble, processes: ScriptedProcessRunner):
        self.forge = forge
        self.processes = processes
        self.moved = ScriptedProcessRunner(
            {("git", "rev-parse", "--verify"): ProcessAnswer(stdout=f"{HEAD_OF_THE_WAVE_AFTER_THE_MERGE}\n")}
        )

    def run(self, request):
        if self.forge.merges and request.argv[:3] == ("git", "rev-parse", "--verify"):
            return self.moved.run(request)
        return self.processes.run(request)


class TickReadingTheReferencesOfAWaveItMovedTest(unittest.TestCase):
    def test_should_read_the_references_of_each_task_again_on_the_wave_branch_the_merge_moved(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        (root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        (root / "cache" / "refs" / "tidepool" / HEAD_OF_THE_WAVE_AFTER_THE_MERGE).mkdir(parents=True)
        repository = root / "tidepool"
        (repository / ".brigade" / "worktrees" / "T8").mkdir(parents=True)
        write_ledger(root, LEDGER_OF_A_VERIFIED_TASK)
        corpus = {
            "STUDY": {"triage": PAUSED_TRIAGE},
            "PROJECT": {"tidepool": (("PATH", str(repository)), ("MAIN", "main"), ("FORGE", "github"))},
            "TASK": {"T7": TASK_DELIVERED, "T8": TASK_AFTER_T7},
        }
        processes = ScriptedProcessRunner(MACHINE_ANSWERS, fallback=create_corpus_double(corpus))
        forge = MergingForgeDouble({"feature/T7-tide-table": GREEN_PULL_REQUEST})
        runtime = create_test_runtime(
            create_test_paths(root),
            run_process=WaveBranchMovedByTheMergeDouble(forge, processes).run,
            spawn_process=SpawnRecorderDouble().spawn,
            resolve_plugin=_resolve_the_collectors_beside(create_plugin_resolution(STEP_COUNTING_PROBE, forge), root),
        )

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        wave_tree = str(root / "cache" / "refs" / "tidepool" / WAVE_HEAD)
        moved_wave_tree = str(root / "cache" / "refs" / "tidepool" / HEAD_OF_THE_WAVE_AFTER_THE_MERGE)
        self.assertEqual(
            select_argvs_opening_on(processes.argvs, ("awawa", "refs")),
            [
                ("awawa", "refs", "@TASK.T7", "--json", wave_tree),
                ("awawa", "refs", "@TASK.T8", "--json", wave_tree),
                ("awawa", "refs", "@TASK.T7", "--json", moved_wave_tree),
                ("awawa", "refs", "@TASK.T8", "--json", moved_wave_tree),
            ],
        )


TASK_NAMING_NO_MILESTONE_PARKED = (("TITLE", "Tide table"), ("TYPE", "feat"), ("STATUS", "todo"))
WAVE_OF_NO_MILESTONE_STARTED = {
    "schema_version": 2,
    "ts": "2026-10-18T09:00:00Z",
    "event": "wave.started",
    "wave": "tidepool_w16",
    "project": "tidepool",
    "tasks": ["T7"],
}
PULL_REQUEST_OF_T7_INTO_MAIN = {**INTEGRATION_PULL_REQUEST_OPEN_INTO_MAIN, "number": 212}


class TickReportingATaskNamingNoMilestoneTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        self.repository = self.root / "tidepool"
        (self.repository / ".brigade" / "worktrees" / "T7").mkdir(parents=True)
        self.forge = OpeningForgeDouble({"feature/T7-tide-table": PULL_REQUEST_OF_T7_INTO_MAIN})
        self.spawn = SpawnRecorderDouble()
        write_ledger(self.root, [WAVE_OF_NO_MILESTONE_STARTED, _record_task_state("parked")])

    def _create_runtime(self, forge_name: str = "github") -> Runtime:
        corpus = {
            "STUDY": PAUSED_BUILT_IN_STUDIES,
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"), ("FORGE", forge_name))},
            "TASK": {"T7": TASK_NAMING_NO_MILESTONE_PARKED},
            "MILESTONE": {},
            "REQUEST": NO_REQUEST,
        }
        return create_test_runtime(
            create_test_paths(self.root),
            run_process=ScriptedProcessRunner(
                {**MACHINE_ANSWERS, ("git", "ls-remote"): ProcessAnswer(stdout="")},
                fallback=create_corpus_double(corpus),
            ).run,
            spawn_process=self.spawn.spawn,
            resolve_plugin=_resolve_the_collectors_beside(
                create_plugin_resolution(STEP_COUNTING_PROBE, self.forge), self.root
            ),
        )

    def _read_reported_tasks(self) -> list[dict]:
        return select_reported_tasks(
            map(json.loads, (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8").splitlines())
        )

    def test_should_record_the_report_of_a_parked_task_with_the_run_it_detaches_and_the_login_of_the_cli(self):
        # Act
        COMMAND.run(Namespace(mode="once"), self._create_runtime())

        # Assert
        reported_run = self.spawn.argvs[0][-1]
        self.assertEqual(self.spawn.argvs[0], ("study", "run", "task-report", "--run-id", reported_run))
        self.assertEqual(
            self._read_reported_tasks(),
            [
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.reported",
                    "project": "tidepool",
                    "task": "T7",
                    "run": reported_run,
                    "login": "tidepool-cli",
                }
            ],
        )

    def test_should_record_the_report_of_a_project_without_a_forge_with_no_login(self):
        # Act
        COMMAND.run(Namespace(mode="once"), self._create_runtime(forge_name="none"))

        # Assert
        reported_run = self.spawn.argvs[0][-1]
        self.assertEqual(
            self._read_reported_tasks(),
            [
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.reported",
                    "project": "tidepool",
                    "task": "T7",
                    "run": reported_run,
                    "login": None,
                }
            ],
        )


CLOSE_OF_M4 = {
    "schema_version": 1,
    "ts": "2026-10-19T09:30:00Z",
    "event": "milestone.closed",
    "project": "tidepool",
    "milestone": "M4",
    "pr": 90,
}
DELETION_OF_THE_MILESTONE_BRANCH = ("git", "branch", "--quiet", "-D", "integration/tides")
MILESTONE_BRANCH_WITHIN_MAIN = ("git", "merge-base", "--is-ancestor", WAVE_HEAD, "main")


CUT_OF_M5 = {**CUT_OF_M4, "milestone": "M5", "branch": "integration/reefs"}
CLOSE_OF_M5 = {**CLOSE_OF_M4, "milestone": "M5", "pr": 92}
REEFS_HEAD = "a1b2c3d"
HEAD_OF_THE_REEFS_BRANCH = ("git", "rev-parse", "--verify", "--quiet", "refs/heads/integration/reefs")
BRANCH_DELETION = ("git", "branch", "--quiet", "-D")


class IntegrationBranchDeletingRunnerDouble(ScriptedProcessRunner):
    def run(self, request):
        record = super().run(request)
        if request.argv[: len(BRANCH_DELETION)] == BRANCH_DELETION:
            self.answers[("git", "rev-parse", "--verify", "--quiet", f"refs/heads/{request.argv[-1]}")] = ProcessAnswer(
                exit_code=1
            )
        return record


class TickRemovingTheBranchOfAClosedMilestoneTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        self.worktree = self.root / "tidepool" / ".brigade" / "worktrees" / "integration-tides"
        self.worktree.mkdir(parents=True)
        write_ledger(self.root, [CUT_OF_M4, CLOSE_OF_M4])
        corpus = {
            "STUDY": PAUSED_BUILT_IN_STUDIES,
            "PROJECT": {"tidepool": (("PATH", str(self.root / "tidepool")), ("MAIN", "main"))},
            "TASK": {},
        }
        self.machine = IntegrationBranchDeletingRunnerDouble(
            {
                **MACHINE_ANSWERS,
                ("awawa", "status", "MILESTONE"): NO_ACTIVE_MILESTONE,
                ("git", "worktree", "remove"): ProcessAnswer(),
                DELETION_OF_THE_MILESTONE_BRANCH: ProcessAnswer(),
            },
            fallback=create_corpus_double(corpus),
        )
        self.runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=self.machine.run,
            resolve_plugin=create_plugin_resolution(
                STEP_COUNTING_PROBE, create_forge(NO_PULL_REQUEST, NO_DETAILS_ASKED)
            ),
        )

    def test_should_remove_the_worktree_then_the_local_branch_of_the_closed_milestone(self):
        # Act
        COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(
            select_argvs_opening_on(self.machine.argvs, ("git", "worktree", "remove"), ("git", "branch", "--quiet")),
            [("git", "worktree", "remove", "--force", str(self.worktree)), DELETION_OF_THE_MILESTONE_BRANCH],
        )

    def test_should_name_on_stderr_the_branch_of_the_closed_milestone_it_keeps_with_its_reason(self):
        # Arrange
        self.machine.answers[MILESTONE_BRANCH_WITHIN_MAIN] = ProcessAnswer(exit_code=1)
        errors = io.StringIO()

        # Act
        with contextlib.redirect_stderr(errors):
            COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertIn(
            "brigade tick: the branch integration/tides of tidepool kept: a commit outside the merged pull request\n",
            errors.getvalue(),
        )

    def test_should_name_the_branch_it_keeps_once_in_a_tick_of_several_rounds(self):
        # Arrange
        write_ledger(self.root, [CUT_OF_M4, CLOSE_OF_M4, CUT_OF_M5, CLOSE_OF_M5])
        self.machine.answers[MILESTONE_BRANCH_WITHIN_MAIN] = ProcessAnswer(exit_code=1)
        self.machine.answers[HEAD_OF_THE_REEFS_BRANCH] = ProcessAnswer(stdout=f"{REEFS_HEAD}\n")
        self.machine.answers[("git", "branch", "--quiet", "-D", "integration/reefs")] = ProcessAnswer()
        errors = io.StringIO()

        # Act
        with contextlib.redirect_stderr(errors):
            COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(errors.getvalue().count("the branch integration/tides of tidepool kept"), 1)

    def test_should_remove_nothing_of_the_branch_it_keeps(self):
        # Arrange
        self.machine.answers[MILESTONE_BRANCH_WITHIN_MAIN] = ProcessAnswer(exit_code=1)

        # Act
        with contextlib.redirect_stderr(io.StringIO()):
            COMMAND.run(Namespace(mode="once"), self.runtime)

        # Assert
        self.assertNotIn(DELETION_OF_THE_MILESTONE_BRANCH, self.machine.argvs)

    def test_should_name_the_branch_it_keeps_with_its_reason_on_a_dry_run(self):
        # Arrange
        self.machine.answers[MILESTONE_BRANCH_WITHIN_MAIN] = ProcessAnswer(exit_code=1)

        # Act
        document = COMMAND.run(Namespace(mode="dry-run"), self.runtime)

        # Assert
        self.assertEqual(
            document["plan"],
            [
                {
                    "project": "tidepool",
                    "branch": "integration/tides",
                    "reason": "a commit outside the merged pull request",
                }
            ],
        )


MILESTONE_PULL_REQUEST_OPEN = {**INTEGRATION_PULL_REQUEST_OPEN_INTO_MAIN, "number": 77}
MILESTONE_M4_WITH_ITS_SUBJECT = (("STATUS", "active"), ("TITLE", "Tides"), ("SUBJECT", "chart the tides"))
TITLE_OF_WHAT_THE_MILESTONE_DELIVERS = "feat: chart the tides (M4)"
MILESTONE_PR_DESCRIBED_AT_THE_HEAD = {
    "schema_version": 1,
    "ts": "2026-10-18T14:00:00Z",
    "event": "milestone.pr_described",
    "project": "tidepool",
    "milestone": "M4",
    "pr": 77,
    "head": "8885daa",
    "login": "tidepool-cli",
}


class DescribingForgeDouble(OpeningForgeDouble):
    def __init__(self, titles: dict):
        super().__init__({MILESTONE_BRANCH: MILESTONE_PULL_REQUEST_OPEN})
        self.titles = titles
        self.edited = []

    def read_pull_request(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "pull_request": {**PULL_REQUEST_DETAILS, "title": self.titles[request["number"]]}}

    def edit_pull_request(self, request: dict, runtime) -> dict:
        self.edited.append(request)
        return {"schema_version": 1}


class RepositoryMissingTheHeadPushedOnTheForgeDouble:
    def __init__(self, run_process):
        self.run_process = run_process
        self.holds_the_head = False

    def push_the_head_on_the_forge(self) -> None:
        self.holds_the_head = False

    def run(self, request: ProcessRequest) -> ProcessRecord:
        if request.argv[:2] == ("git", "fetch") and MILESTONE_BRANCH in request.argv:
            self.holds_the_head = True
        if (
            request.argv[:2] == ("git", "rev-parse")
            and request.argv[-1] == f"{WAVE_HEAD}^{{commit}}"
            and not self.holds_the_head
        ):
            return answer(request, "", 1)
        return self.run_process(request)


class ForgeMovingTheHeadOfTheMilestoneDouble(DescribingForgeDouble):
    def __init__(self, titles: dict, repository: RepositoryMissingTheHeadPushedOnTheForgeDouble):
        super().__init__(titles)
        self.repository = repository

    def find_pull_request(self, request: dict, runtime) -> dict:
        self.repository.push_the_head_on_the_forge()
        return super().find_pull_request(request, runtime)


class TickDescribingThePullRequestOfAMilestoneTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        self.repository = self.root / "tidepool"
        write_ledger(
            self.root, [WAVE_STARTED, _record_task_state("merged"), CUT_OF_M4, WAVE_CLOSED, MILESTONE_PR_OPENED]
        )

    def _create_machine(self):
        corpus = {
            "STUDY": PAUSED_BUILT_IN_STUDIES,
            "PROJECT": {"tidepool": (("PATH", str(self.repository)), ("MAIN", "main"), ("FORGE", "github"))},
            "TASK": {"T7": TASK_DELIVERED},
            "MILESTONE": {"M4": MILESTONE_M4_WITH_ITS_SUBJECT},
        }
        return create_machine_double(
            corpus, {**MACHINE_OUTPUTS, **WAVE_TREE_HOLDING_T7_IMPLEMENTED_OUTPUTS, ("git", "ls-remote"): ""}
        )

    def _create_runtime(self, forge: DescribingForgeDouble, run_process=None) -> Runtime:
        return create_test_runtime(
            create_test_paths(self.root),
            run_process=run_process or self._create_machine(),
            spawn_process=SpawnRecorderDouble().spawn,
            resolve_plugin=_resolve_the_collectors_beside(
                create_plugin_resolution(STEP_COUNTING_PROBE, forge), self.root
            ),
        )

    def _read_last_event(self) -> dict:
        return json.loads(
            (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8").splitlines()[-1]
        )

    def test_should_retitle_the_pull_request_of_the_milestone_by_what_its_head_delivers(self):
        # Arrange
        forge = DescribingForgeDouble({77: "chore(milestone): merge the milestone M4 into main"})

        # Act
        COMMAND.run(Namespace(mode="once"), self._create_runtime(forge))

        # Assert
        self.assertEqual(
            forge.edited,
            [
                {
                    "repository": str(self.repository),
                    "number": 77,
                    "title": TITLE_OF_WHAT_THE_MILESTONE_DELIVERS,
                    "environment": {},
                }
            ],
        )
        self.assertEqual(self._read_last_event(), {**MILESTONE_PR_DESCRIBED_AT_THE_HEAD, "ts": ANY})

    def test_should_fetch_the_branch_of_the_milestone_to_read_a_head_pushed_on_the_forge_since_the_last_fetch(self):
        # Arrange
        repository = RepositoryMissingTheHeadPushedOnTheForgeDouble(self._create_machine())
        forge = ForgeMovingTheHeadOfTheMilestoneDouble(
            {77: "chore(milestone): merge the milestone M4 into main"}, repository
        )

        # Act
        COMMAND.run(Namespace(mode="once"), self._create_runtime(forge, repository.run))

        # Assert
        self.assertEqual(
            forge.edited,
            [
                {
                    "repository": str(self.repository),
                    "number": 77,
                    "title": TITLE_OF_WHAT_THE_MILESTONE_DELIVERS,
                    "environment": {},
                }
            ],
        )
        self.assertEqual(self._read_last_event(), {**MILESTONE_PR_DESCRIBED_AT_THE_HEAD, "ts": ANY})

    def test_should_record_the_head_described_without_retitling_a_pull_request_already_titled_so(self):
        # Arrange
        forge = DescribingForgeDouble({77: TITLE_OF_WHAT_THE_MILESTONE_DELIVERS})

        # Act
        COMMAND.run(Namespace(mode="once"), self._create_runtime(forge))

        # Assert
        self.assertEqual(forge.edited, [])
        self.assertEqual(self._read_last_event(), {**MILESTONE_PR_DESCRIBED_AT_THE_HEAD, "ts": ANY})

    def test_should_describe_no_head_already_described(self):
        # Arrange
        write_ledger(
            self.root,
            [
                WAVE_STARTED,
                _record_task_state("merged"),
                CUT_OF_M4,
                WAVE_CLOSED,
                MILESTONE_PR_OPENED,
                MILESTONE_PR_DESCRIBED_AT_THE_HEAD,
            ],
        )
        forge = DescribingForgeDouble({77: "chore: an older title"})

        # Act
        COMMAND.run(Namespace(mode="once"), self._create_runtime(forge))

        # Assert
        self.assertEqual(forge.edited, [])
        self.assertEqual(self._read_last_event(), MILESTONE_PR_DESCRIBED_AT_THE_HEAD)

    def test_should_print_the_describe_with_its_milestone_its_pull_request_and_its_head_on_a_dry_run(self):
        # Arrange
        forge = DescribingForgeDouble({77: "chore: an older title"})

        # Act
        document = COMMAND.run(Namespace(mode="dry-run"), self._create_runtime(forge))

        # Assert
        self.assertIn(
            {"project": "tidepool", "milestone": "M4", "branch": "integration/tides", "pr": 77, "head": "8885daa"},
            document["plan"],
        )


ACCEPTANCE_COMMAND = "python3 -m unittest"


class TickPreflightingATaskDeliveredWithoutAForgeTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        self.repository = self.root / "tidepool"
        delivered_run = {**create_run_record(FIRST_RUN, WAVE, "T7"), "project": "tidepool"}
        write_run(self.root / "state", delivered_run, create_run_result(FIRST_RUN, "done", "2026-10-18T10:30:00Z"))
        delivered = {**create_run_result(FIRST_RUN, "done", "2026-10-18T10:30:00Z"), "wave": WAVE, "task": "T7"}
        self.delivered = delivered
        write_ledger(self.root, [WAVE_STARTED, _record_task_state("running"), delivered])
        self.worktree = self.repository / ".brigade" / "worktrees" / "T7"
        self.spawn = SpawnRecorderDouble()

    def _create_runtime(self, acceptance_outputs: dict) -> Runtime:
        project = (
            ("PATH", str(self.repository)),
            ("MAIN", "main"),
            ("FORGE", "none"),
            ("ACCEPTANCE", ACCEPTANCE_COMMAND),
        )
        corpus = {"STUDY": PAUSED_BUILT_IN_STUDIES, "PROJECT": {"tidepool": project}, "TASK": {"T7": TASK_DELIVERED}}
        return create_test_runtime(
            create_test_paths(self.root),
            run_process=create_machine_double(corpus, {**MACHINE_OUTPUTS, **acceptance_outputs}),
            spawn_process=self.spawn.spawn,
            resolve_plugin=_resolve_the_collectors_beside(
                create_plugin_resolution(STEP_COUNTING_PROBE, create_forge(NO_PULL_REQUEST, NO_DETAILS_ASKED)),
                self.root,
            ),
        )

    def _read_events_of_the_tick(self) -> list[dict]:
        events = (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8").splitlines()
        return list(map(json.loads, events[3:]))

    def test_should_hold_for_verification_the_head_its_build_run_delivered_once_its_acceptance_passes(self):
        # Arrange
        passing_acceptance = {("python3", "-m", "unittest"): ""}
        runtime = self._create_runtime(passing_acceptance)

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(
            self._read_events_of_the_tick(),
            [
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.preflighted",
                    "project": "tidepool",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "head": "8885daa",
                    "checks": [
                        {"name": "ancestry", "verdict": "pass", "findings": []},
                        {
                            "name": "acceptance",
                            "verdict": "pass",
                            "findings": [],
                            "commands": [{"command": "python3 -m unittest", "exit_code": 0}],
                        },
                        {"name": "corpus", "verdict": "pass", "findings": []},
                        {"name": "promotion", "verdict": "pass", "findings": []},
                        {"name": "untouched_files", "verdict": "pass", "findings": []},
                        {"name": "privacy", "verdict": "pass", "findings": []},
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

    def test_should_launch_the_verification_of_its_delivered_head_naming_no_pull_request(self):
        # Arrange
        self.worktree.mkdir(parents=True)
        preflighted = {**TASK_PREFLIGHTED_AT_THE_HEAD, "pr": None}
        write_ledger(
            self.root,
            [WAVE_STARTED, _record_task_state("running"), self.delivered, preflighted, _record_task_state("verifying")],
        )
        no_acceptance_run = {}

        # Act
        COMMAND.run(Namespace(mode="once"), self._create_runtime(no_acceptance_run))

        # Assert
        self.assertEqual(
            self.spawn.argvs,
            [
                (
                    "run",
                    "verify-pr",
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


FORGELESS_RUN = "20261018T100000Z-e5f6a7"
NO_MILESTONE_TASK = (("TITLE", "Tide table"), ("TYPE", "feat"), ("STATUS", "implemented"))
VERDICT_OFF_A_FORGE = {
    "schema_version": 1,
    "ts": "2026-10-18T11:45:00Z",
    "event": "task.verdict",
    "project": "tidepool",
    "wave": "tidepool_w16",
    "task": "T7",
    "head": "8885daa",
    "verdict": "pass",
    "findings": [],
    "login": None,
}
MILESTONE_REPORTED_ON_M4 = {
    "schema_version": 1,
    "ts": "2026-10-18T12:00:00Z",
    "event": "milestone.reported",
    "project": "tidepool",
    "milestone": "M4",
    "run": FORGELESS_RUN,
    "login": None,
}
REPORT_ORDER_DONE = {
    "schema_version": 1,
    "ts": "2026-10-18T12:05:00Z",
    "event": "order.done",
    "project": "tidepool",
    "kind": "study",
    "order": None,
    "run": FORGELESS_RUN,
}
TO_MAIN_NOT_MERGED = {("git", "merge-base", "--is-ancestor"): ProcessAnswer(exit_code=1)}
POLICY_OF_NO_AUTO_MERGE = {"tidepool_policy": (("PROJECT", "@PROJECT.tidepool"), ("AUTO_MERGE", "none"))}
MERGE_AND_TREE_OUTPUTS = {
    ("git", "merge", "--quiet"): "",
    ("git", "reset"): "",
}


class TickEndingATaskOfAProjectWithoutAForgeTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
        self.repository = self.root / "tidepool"
        write_run(
            self.root / "state",
            {**create_run_record(FIRST_RUN, WAVE, "T7"), "project": "tidepool"},
            create_run_result(FIRST_RUN, "done", "2026-10-18T10:30:00Z"),
        )
        self.delivered = {**create_run_result(FIRST_RUN, "done", "2026-10-18T10:30:00Z"), "wave": WAVE, "task": "T7"}
        self.verified_events = [
            WAVE_STARTED,
            _record_task_state("running"),
            self.delivered,
            {**TASK_PREFLIGHTED_AT_THE_HEAD, "pr": None},
            _record_task_state("verifying"),
            VERDICT_OFF_A_FORGE,
            _record_task_state("verified"),
        ]

    def _create_runtime(
        self, task: tuple, answers: dict, milestones: dict | None = None, policies: dict | None = None
    ) -> Runtime:
        project = (("PATH", str(self.repository)), ("MAIN", "main"), ("FORGE", "none"))
        corpus = {
            "STUDY": PAUSED_BUILT_IN_STUDIES,
            "PROJECT": {"tidepool": project},
            "TASK": {"T7": task},
            "MILESTONE": milestones or {},
            "POLICY": policies or {},
        }
        machine = create_machine_double(corpus, {**MACHINE_OUTPUTS, **MERGE_AND_TREE_OUTPUTS})
        machine.__self__.answers.update(answers)
        return create_test_runtime(
            create_test_paths(self.root),
            run_process=machine,
            spawn_process=SpawnRecorderDouble().spawn,
            resolve_plugin=_resolve_the_collectors_beside(
                create_plugin_resolution(STEP_COUNTING_PROBE, create_forge(NO_PULL_REQUEST, NO_DETAILS_ASKED)),
                self.root,
            ),
        )

    def _write_events(self, events: list[dict]) -> int:
        write_ledger(self.root, events)
        return len(events)

    def _read_events_since(self, written: int) -> list[dict]:
        events = (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8").splitlines()
        return list(map(json.loads, events[written:]))

    def test_should_record_the_merge_with_no_pull_request_and_close_its_wave_with_none(self):
        # Arrange
        written = self._write_events([CUT_OF_M4, *self.verified_events])
        no_other_answer = {}

        # Act
        COMMAND.run(Namespace(mode="once"), self._create_runtime(TASK_DELIVERED, no_other_answer))

        # Assert
        self.assertEqual(
            self._read_events_since(written)[:3],
            [
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "pr.merged",
                    "project": "tidepool",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "rounds": 1,
                    "login": None,
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "task.state",
                    "wave": "tidepool_w16",
                    "task": "T7",
                    "state": "merged",
                },
                {"schema_version": 1, "ts": "2026-10-19T09:00:00Z", "event": "wave.closed", "wave": "tidepool_w16"},
            ],
        )

    def test_should_merge_the_task_head_into_a_worktree_of_the_branch_of_its_milestone(self):
        # Arrange
        self._write_events([CUT_OF_M4, *self.verified_events])
        runtime = self._create_runtime(TASK_DELIVERED, {})

        # Act
        COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertIn(
            ("git", "merge", "--quiet", "-m", "merge @TASK.T7 into integration/tides", "8885daa"),
            runtime.run_process.__self__.argvs,
        )

    def test_should_park_a_task_whose_merge_conflicts(self):
        # Arrange
        written = self._write_events([CUT_OF_M4, *self.verified_events])
        conflict = {("git", "merge", "--quiet"): ProcessAnswer(exit_code=1)}

        # Act
        COMMAND.run(Namespace(mode="once"), self._create_runtime(TASK_DELIVERED, conflict))

        # Assert
        parked = self._read_events_since(written)[0]
        self.assertEqual(
            parked,
            {
                "schema_version": 1,
                "ts": "2026-10-19T09:00:00Z",
                "event": "task.parked",
                "wave": "tidepool_w16",
                "task": "T7",
                "reason": "the merge into integration/tides conflicted",
                "blockers": [],
            },
        )

    def test_should_open_the_worktree_of_its_milestone_and_name_the_merge_under_no_auto_merge(self):
        # Arrange
        written = self._write_events([CUT_OF_M4, *self.verified_events])
        runtime = self._create_runtime(TASK_DELIVERED, TO_MAIN_NOT_MERGED, policies=POLICY_OF_NO_AUTO_MERGE)

        # Act
        document = COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        worktree = f"{self.repository}/.brigade/worktrees/integration-tides"
        self.assertEqual(document["merge_commands"], [f"git -C {worktree} merge feature/T7-tide-table"])
        self.assertIn(
            ("git", "worktree", "add", "--quiet", worktree, "integration/tides"),
            runtime.run_process.__self__.argvs,
        )
        self.assertEqual(self._read_events_since(written), [])

    def test_should_name_the_worktree_already_holding_its_milestone_branch_and_open_none_under_no_auto_merge(self):
        # Arrange
        self._write_events([CUT_OF_M4, *self.verified_events])
        holding_the_branch = ProcessAnswer(
            stdout="worktree /srv/elsewhere\0HEAD 8885daa\0branch refs/heads/integration/tides\0\0"
        )
        answers = {**TO_MAIN_NOT_MERGED, ("git", "worktree", "list"): holding_the_branch}
        runtime = self._create_runtime(TASK_DELIVERED, answers, policies=POLICY_OF_NO_AUTO_MERGE)

        # Act
        document = COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(document["merge_commands"], ["git -C /srv/elsewhere merge feature/T7-tide-table"])
        self.assertNotIn(
            (
                "git",
                "worktree",
                "add",
                "--quiet",
                f"{self.repository}/.brigade/worktrees/integration-tides",
                "integration/tides",
            ),
            runtime.run_process.__self__.argvs,
        )

    def test_should_record_merged_a_task_once_its_head_is_an_ancestor_of_its_milestone_branch_under_no_auto_merge(self):
        # Arrange
        written = self._write_events([CUT_OF_M4, *self.verified_events])
        in_the_milestone_branch = {("git", "merge-base", "--is-ancestor"): ProcessAnswer()}
        runtime = self._create_runtime(TASK_DELIVERED, in_the_milestone_branch, policies=POLICY_OF_NO_AUTO_MERGE)

        # Act
        document = COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(self._read_events_since(written)[0]["state"], "merged")
        self.assertEqual(document["merge_commands"], [])
        self.assertIn(
            ("git", "merge-base", "--is-ancestor", "8885daa", "integration/tides"),
            runtime.run_process.__self__.argvs,
        )

    def test_should_name_the_command_merging_a_task_of_no_milestone_and_record_nothing(self):
        # Arrange
        written = self._write_events(self.verified_events)
        runtime = self._create_runtime(NO_MILESTONE_TASK, TO_MAIN_NOT_MERGED)

        # Act
        document = COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(document["merge_commands"], [f"git -C {self.repository} merge feature/T7-tide-table"])
        self.assertEqual(self._read_events_since(written), [])

    def test_should_name_the_merge_commands_on_stderr_in_a_loop(self):
        # Arrange
        self._write_events(self.verified_events)
        runtime = self._create_runtime(NO_MILESTONE_TASK, TO_MAIN_NOT_MERGED)
        request = Namespace(mode=LOOP_MODE, create_runtime=_create_round_factory([(runtime, signal.SIGTERM)]))
        stderr = io.StringIO()

        # Act
        with contextlib.redirect_stderr(stderr):
            COMMAND.run(request, runtime)

        # Assert
        self.assertIn(
            f"brigade tick: to merge: git -C {self.repository} merge feature/T7-tide-table\n", stderr.getvalue()
        )

    def test_should_record_merged_a_task_of_no_milestone_the_user_merged_into_main(self):
        # Arrange
        written = self._write_events(self.verified_events)
        merged_into_main = {("git", "merge-base", "--is-ancestor"): ProcessAnswer()}

        # Act
        document = COMMAND.run(Namespace(mode="once"), self._create_runtime(NO_MILESTONE_TASK, merged_into_main))

        # Assert
        self.assertEqual(self._read_events_since(written)[0]["state"], "merged")
        self.assertEqual(document["merge_commands"], [])

    def test_should_name_the_command_merging_a_reported_milestone_into_main(self):
        # Arrange
        self._write_events([CUT_OF_M4, MILESTONE_REPORTED_ON_M4, REPORT_ORDER_DONE])
        runtime = self._create_runtime(TASK_DELIVERED, TO_MAIN_NOT_MERGED)

        # Act
        document = COMMAND.run(Namespace(mode="once"), runtime)

        # Assert
        self.assertEqual(document["merge_commands"], [f"git -C {self.repository} merge integration/tides"])

    def test_should_close_the_milestone_with_no_pull_request_once_its_branch_is_in_main(self):
        # Arrange
        written = self._write_events([CUT_OF_M4, MILESTONE_REPORTED_ON_M4, REPORT_ORDER_DONE])
        branch_in_main = {("git", "merge-base", "--is-ancestor"): ProcessAnswer()}

        # Act
        COMMAND.run(Namespace(mode="once"), self._create_runtime(TASK_DELIVERED, branch_in_main))

        # Assert
        self.assertEqual(
            self._read_events_since(written),
            [
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "milestone.closed",
                    "project": "tidepool",
                    "milestone": "M4",
                }
            ],
        )

    def test_should_order_the_report_of_its_milestone_without_the_pull_requests(self):
        # Arrange
        self._write_events([CUT_OF_M4, *self.verified_events])

        # Act
        COMMAND.run(Namespace(mode="once"), self._create_runtime(TASK_DELIVERED, {}))

        # Assert
        report_run = next((self.root / "state" / "runs").glob("*/study.json"))
        self.assertFalse(json.loads(report_run.read_text())["milestone"]["reads_pull_requests"])
