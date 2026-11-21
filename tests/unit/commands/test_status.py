import dataclasses
import json
import os
import tempfile
import unittest
from argparse import Namespace
from datetime import UTC, datetime
from pathlib import Path

from brigade.commands.status import COMMAND
from brigade.ledger.append_event import append_event
from brigade.ledger.milestone_closed import MilestoneClosed
from brigade.ledger.milestone_pr_opened import MilestonePrOpened
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.order_started import OrderStarted
from brigade.ledger.task_parked import TaskParked
from brigade.ledger.task_state import TaskState
from brigade.ledger.wave_blocked import WaveBlocked
from brigade.ledger.wave_closed import WaveClosed
from brigade.ledger.wave_parked import WaveParked
from brigade.ledger.wave_started import WaveStarted
from brigade.runs.record_run_pid import record_run_pid
from brigade.system.reset_hour import ResetHour
from brigade.system.token_usage import TokenUsage
from tests.unit.commands.command_runtime import create_corpus_double, write_operational_corpus
from tests.unit.commands.inbox_lines import NOTE_ON_OAK_RECORDED, THREAD_DISMISSED, THREAD_RECORDED
from tests.unit.commands.run_directories import FIRST_RUN, SECOND_RUN, create_run_record, write_run
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.ledger.create_run_finished import create_run_finished

OAK = (
    ("PATH", "/srv/oak"),
    ("STATUS", "active"),
    ("FORGE", "github"),
    ("REMOTE", "git@github.com:o/oak.git"),
    ("CORPUS", "corpus"),
)
ELM = (("PATH", "/srv/elm"), ("STATUS", "paused"))
DEBT_STUDY = (
    ("TITLE", "the debt of the code"),
    ("COLLECTOR", "runs-list"),
    ("SLOT", "report"),
    ("EVERY", "1d"),
    ("OUTPUT", "file:/srv/reports/debt.md"),
    ("ANSWER", "ANSWER"),
    ("STATUS", "active"),
)
HEALTH_STUDY = (
    ("TITLE", "the health of the machine"),
    ("COLLECTOR", "runs-list"),
    ("SLOT", "report"),
    ("EVERY", "1d"),
    ("OUTPUT", "file:/srv/reports/health.md"),
    ("ANSWER", "ANSWER"),
    ("STATUS", "paused"),
)
CORPUS = {"PROJECT": {"oak": OAK, "elm": ELM}, "STUDY": {"debt": DEBT_STUDY, "health": HEALTH_STUDY}}
CORPUS_OF_PROJECTS = {"PROJECT": {"oak": OAK, "elm": ELM}}
NIGHTLY_ORDER = (("RECIPE", "usage-report"), ("PROJECT", "@PROJECT.oak"), ("EVERY", "24h"), ("STATUS", "active"))
HOURLY_ORDER = (("RECIPE", "usage-report"), ("PROJECT", "@PROJECT.oak"), ("EVERY", "1h"), ("STATUS", "active"))
CORPUS_OF_ORDERS = {**CORPUS, "ORDER": {"nightly": NIGHTLY_ORDER, "hourly": HOURLY_ORDER}}
PARKED_NIGHTLY = {
    "name": "nightly",
    "recipe": "usage-report",
    "project": "oak",
    "run": "20261019T081500Z-n1",
    "step": "1-gate",
    "reason": "the gate step failed",
    "age_s": 2640,
}
HOME = {
    "schema_version": 1,
    "projects": [
        {"name": "elm", "paused": True, "forge": "none", "remote": None, "corpus": False},
        {"name": "oak", "paused": False, "forge": "github", "remote": "git@github.com:o/oak.git", "corpus": True},
    ],
    "waves": [
        {
            "wave": "oak_w2",
            "project": "oak",
            "branch": "integration/oak_w2",
            "last_event": "wave.blocked",
            "tasks": 2,
            "task_states": {"queued": 2},
            "halt": {"reason": "quota", "resume_at": "2026-10-19T10:00:00Z", "age_s": 6000},
        },
        {
            "wave": "elm_w1",
            "project": "elm",
            "branch": "integration/elm_w1",
            "last_event": "wave.started",
            "tasks": 1,
            "task_states": {"queued": 1},
            "halt": None,
        },
    ],
    "live_runs": [],
    "awaiting_merge": [],
    "inbox": {"new_signals": 1, "scans": [], "stalls": []},
    "quota": {
        "window_hours": 5,
        "usage": {
            "input_tokens": 10,
            "output_tokens": 20,
            "cache_creation_input_tokens": 30,
            "cache_read_input_tokens": 40,
        },
        "runs_without_usage": 1,
        "blocked_waves": [{"wave": "oak_w2", "project": "oak", "resume_at": "2026-10-19T10:00:00Z"}],
    },
    "last_tick": {"ts": "2026-10-19T08:55:00Z", "duration_ms": 120, "actions_applied": 2},
    "studies": [
        {
            "name": "debt",
            "project": None,
            "status": "active",
            "every": "1d",
            "last_run": "20261019T080000Z-d1",
            "outcome": "parked",
            "due": False,
        },
        {
            "name": "triage",
            "project": None,
            "status": "active",
            "every": "24h",
            "last_run": None,
            "outcome": None,
            "due": True,
        },
        {
            "name": "mine_transcripts",
            "project": None,
            "status": "active",
            "every": "mon@09:00",
            "last_run": None,
            "outcome": None,
            "due": True,
        },
        {
            "name": "corpus_lint_elm",
            "project": "elm",
            "status": "active",
            "every": "24h",
            "last_run": None,
            "outcome": None,
            "due": True,
        },
        {
            "name": "corpus_fmt_elm",
            "project": "elm",
            "status": "active",
            "every": "24h",
            "last_run": None,
            "outcome": None,
            "due": True,
        },
        {
            "name": "stale_branches_elm",
            "project": "elm",
            "status": "active",
            "every": "24h",
            "last_run": None,
            "outcome": None,
            "due": True,
        },
        {
            "name": "worktrees_elm",
            "project": "elm",
            "status": "active",
            "every": "24h",
            "last_run": None,
            "outcome": None,
            "due": True,
        },
        {
            "name": "corpus_lint_oak",
            "project": "oak",
            "status": "active",
            "every": "24h",
            "last_run": None,
            "outcome": None,
            "due": True,
        },
        {
            "name": "corpus_fmt_oak",
            "project": "oak",
            "status": "active",
            "every": "24h",
            "last_run": None,
            "outcome": None,
            "due": True,
        },
        {
            "name": "stale_branches_oak",
            "project": "oak",
            "status": "active",
            "every": "24h",
            "last_run": None,
            "outcome": None,
            "due": True,
        },
        {
            "name": "worktrees_oak",
            "project": "oak",
            "status": "active",
            "every": "24h",
            "last_run": None,
            "outcome": None,
            "due": True,
        },
    ],
    "orders": [],
}


STALE_BRANCH_ON_ELM_RECORDED = (
    '{"schema_version": 1, "ts": "2026-10-19T08:45:00Z", "event": "recorded", "kind": "scan", "project": "elm",'
    ' "fingerprint": "stale_branches_elm:elm:feature/x", "evidence": {"fingerprint": "feature/x"}}\n'
)
LINT_ON_OAK_RECORDED_FIRST = (
    '{"schema_version": 1, "ts": "2026-10-19T07:00:00Z", "event": "recorded", "kind": "scan", "project": "oak",'
    ' "fingerprint": "corpus_lint_oak:oak:L001:corpus/tasks.awawa:TASK.B1", "evidence": {"fingerprint": "L001"}}\n'
)
LINT_ON_OAK_RECORDED_AGAIN = (
    '{"schema_version": 1, "ts": "2026-10-19T08:30:00Z", "event": "recorded", "kind": "scan", "project": "oak",'
    ' "fingerprint": "corpus_lint_oak:oak:L001:corpus/tasks.awawa:TASK.B1", "evidence": {"fingerprint": "L001"}}\n'
)
OTHER_LINT_ON_OAK_RECORDED = (
    '{"schema_version": 1, "ts": "2026-10-19T08:00:00Z", "event": "recorded", "kind": "scan", "project": "oak",'
    ' "fingerprint": "corpus_lint_oak:oak:L002:corpus/decisions.awawa:none", "evidence": {"fingerprint": "L002"}}\n'
)
WORKTREE_ON_OAK_RECORDED = (
    '{"schema_version": 1, "ts": "2026-10-19T06:00:00Z", "event": "recorded", "kind": "scan", "project": "oak",'
    ' "fingerprint": "worktrees_oak:oak:/srv/oak/.brigade/worktrees/B9", "evidence": {"fingerprint": "B9"}}\n'
)
WORKTREE_ON_OAK_DISMISSED = (
    '{"schema_version": 1, "ts": "2026-10-19T06:30:00Z", "event": "dismissed",'
    ' "fingerprint": "worktrees_oak:oak:/srv/oak/.brigade/worktrees/B9"}\n'
)


STALL_OF_B2_RECORDED = (
    '{"schema_version": 1, "ts": "2026-10-19T08:40:00Z", "event": "recorded", "kind": "stall", "project": "oak",'
    ' "fingerprint": "stall:oak:oak_w2:B2",'
    ' "evidence": {"wave": "oak_w2", "task": "B2", "last_action": "2026-10-19T07:00:00Z"}}\n'
)
STALL_OF_B3_RECORDED = (
    '{"schema_version": 1, "ts": "2026-10-19T08:41:00Z", "event": "recorded", "kind": "stall", "project": "oak",'
    ' "fingerprint": "stall:oak:oak_w2:B3",'
    ' "evidence": {"wave": "oak_w2", "task": "B3", "last_action": "2026-10-19T07:00:00Z"}}\n'
)


def at(hour: int, minute: int) -> datetime:
    return datetime(2026, 10, 19, hour, minute, tzinfo=UTC)


class StatusOfTheMachineTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.paths = create_test_paths(self.root)

    def write_machine(self) -> None:
        write_operational_corpus(self.root)
        (self.root / "state" / "inbox").mkdir(parents=True)
        (self.root / "state" / "inbox" / "signals.jsonl").write_text(
            NOTE_ON_OAK_RECORDED + THREAD_RECORDED + THREAD_DISMISSED, encoding="utf-8"
        )
        (self.root / "state" / "tick.json").write_text(
            json.dumps({"schema_version": 1, "ts": "2026-10-19T08:55:00Z", "duration_ms": 120, "actions_applied": 2}),
            encoding="utf-8",
        )
        events = [
            (at(1, 0), WaveStarted(wave="oak_w1", project="oak", branch="integration/oak_w1", tasks=("B1",))),
            (at(1, 30), WaveClosed(wave="oak_w1", pr=12)),
            (at(5, 0), WaveStarted(wave="oak_w2", project="oak", branch="integration/oak_w2", tasks=("B2", "B3"))),
            (at(6, 0), WaveStarted(wave="elm_w1", project="elm", branch="integration/elm_w1", tasks=("E1",))),
            (at(7, 0), dataclasses.replace(create_run_finished("r1"), usage=TokenUsage(10, 20, 30, 40))),
            (at(7, 10), create_run_finished("r2")),
            (at(7, 20), WaveBlocked(wave="oak_w2", reason="quota", resume_at="2026-10-19T10:00:00Z")),
            (at(8, 0), OrderStarted(project=None, kind="study", order="debt", run="20261019T080000Z-d1")),
            (
                at(8, 10),
                OrderParked(
                    project=None, kind="study", order="debt", run="20261019T080000Z-d1", step="collect", reason="boom"
                ),
            ),
        ]
        for instant, event in events:
            append_event(self.paths, instant, event)

    def test_should_gather_the_home_document(self):
        # Arrange
        self.write_machine()
        runtime = create_test_runtime(self.paths, run_process=create_corpus_double(CORPUS))

        # Act
        document = COMMAND.run(Namespace(), runtime)

        # Assert
        self.assertEqual(document, HOME)

    def test_should_count_the_tasks_of_each_open_wave_by_state(self):
        # Arrange
        self.write_machine()
        append_event(self.paths, at(8, 20), TaskState(wave="oak_w2", task="B2", state="running", reason=None))
        append_event(self.paths, at(8, 25), TaskParked(wave="oak_w2", task="B3", reason="a question", blockers=()))
        runtime = create_test_runtime(self.paths, run_process=create_corpus_double(CORPUS))

        # Act
        document = COMMAND.run(Namespace(), runtime)

        # Assert
        self.assertEqual(document["waves"][0]["task_states"], {"running": 1, "parked": 1})

    def test_should_list_each_live_run_with_its_slot_its_project_its_wave_and_its_task(self):
        # Arrange
        self.write_machine()
        live = write_run(self.paths.state_root, create_run_record(FIRST_RUN, "oak_w2", "B2"), None)
        record_run_pid(live, os.getpid())
        write_run(self.paths.state_root, create_run_record(SECOND_RUN, "oak_w2", "B3"), None)
        runtime = create_test_runtime(self.paths, run_process=create_corpus_double(CORPUS))

        # Act
        document = COMMAND.run(Namespace(), runtime)

        # Assert
        self.assertEqual(
            document["live_runs"],
            [{"run": FIRST_RUN, "slot": "build", "project": None, "wave": "oak_w2", "task": "B2"}],
        )

    def test_should_list_the_pull_request_of_a_milestone_waiting_for_the_merge_of_the_user(self):
        # Arrange
        self.write_machine()
        append_event(self.paths, at(8, 20), MilestonePrOpened(project="oak", milestone="M1", pr=30, login=None))
        append_event(self.paths, at(8, 25), MilestoneClosed(project="oak", milestone="M1", pr=30))
        append_event(self.paths, at(8, 30), MilestonePrOpened(project="oak", milestone="M2", pr=31, login=None))
        runtime = create_test_runtime(self.paths, run_process=create_corpus_double(CORPUS))

        # Act
        document = COMMAND.run(Namespace(), runtime)

        # Assert
        self.assertEqual(
            document["awaiting_merge"],
            [{"project": "oak", "repository": "/srv/oak", "milestone": "M2", "pr": 31, "age_s": 1800}],
        )

    def test_should_list_each_new_stall_signal_saying_whether_its_task_merged_since(self):
        # Arrange
        self.write_machine()
        (self.root / "state" / "inbox" / "signals.jsonl").write_text(
            STALL_OF_B2_RECORDED + STALL_OF_B3_RECORDED, encoding="utf-8"
        )
        append_event(self.paths, at(8, 50), TaskState(wave="oak_w2", task="B2", state="merged", reason=None))
        append_event(self.paths, at(8, 52), TaskState(wave="oak_w2", task="B3", state="running", reason=None))
        runtime = create_test_runtime(self.paths, run_process=create_corpus_double(CORPUS))

        # Act
        document = COMMAND.run(Namespace(), runtime)

        # Assert
        self.assertEqual(
            document["inbox"]["stalls"],
            [
                {"project": "oak", "wave": "oak_w2", "task": "B2", "merged": True},
                {"project": "oak", "wave": "oak_w2", "task": "B3", "merged": False},
            ],
        )

    def test_should_leave_out_of_the_quota_a_wave_parked_on_another_reason(self):
        # Arrange
        self.write_machine()
        append_event(self.paths, at(8, 20), WaveParked(wave="elm_w1", reason="forge_account"))
        runtime = create_test_runtime(self.paths, run_process=create_corpus_double(CORPUS))

        # Act
        document = COMMAND.run(Namespace(), runtime)

        # Assert
        self.assertEqual(
            document["quota"]["blocked_waves"],
            [{"wave": "oak_w2", "project": "oak", "resume_at": "2026-10-19T10:00:00Z"}],
        )

    def test_should_list_due_a_study_parked_by_a_rate_limit_whose_reset_has_passed(self):
        # Arrange
        self.write_machine()
        judging_run = "20261019T080500Z-j1"
        write_run(
            self.paths.state_root,
            {
                **create_run_record(judging_run, None, None),
                "arguments": {"study": "debt", "run": "20261019T080000Z-d1"},
            },
            None,
        )
        cut = dataclasses.replace(
            create_run_finished(judging_run, outcome="failed", error_class="rate_limit"),
            reset=ResetHour(hour="08:30", timezone="UTC"),
        )
        append_event(self.paths, at(8, 11), cut)
        append_event(
            self.paths,
            at(8, 11),
            OrderParked(
                project=None,
                kind="study",
                order="debt",
                run="20261019T080000Z-d1",
                step="judge",
                reason=f"the judging run {judging_run} gave no answer",
            ),
        )
        runtime = create_test_runtime(self.paths, run_process=create_corpus_double(CORPUS))

        # Act
        document = COMMAND.run(Namespace(), runtime)

        # Assert
        self.assertEqual(
            document["studies"][0],
            {
                "name": "debt",
                "project": None,
                "status": "active",
                "every": "1d",
                "last_run": "20261019T080000Z-d1",
                "outcome": "parked",
                "due": True,
            },
        )

    def test_should_list_the_parked_orders_with_the_step_and_the_reason_that_parked_them(self):
        # Arrange
        self.write_machine()
        events = [
            (at(8, 15), OrderStarted(project="oak", kind="usage-report", order="nightly", run="20261019T081500Z-n1")),
            (
                at(8, 16),
                OrderParked(
                    project="oak",
                    kind="usage-report",
                    order="nightly",
                    run="20261019T081500Z-n1",
                    step="1-gate",
                    reason="the gate step failed",
                ),
            ),
            (at(8, 20), OrderStarted(project="oak", kind="usage-report", order="hourly", run="20261019T082000Z-h1")),
        ]
        for instant, event in events:
            append_event(self.paths, instant, event)
        runtime = create_test_runtime(self.paths, run_process=create_corpus_double(CORPUS_OF_ORDERS))

        # Act
        document = COMMAND.run(Namespace(), runtime)

        # Assert
        self.assertEqual(document["orders"], [PARKED_NIGHTLY])


class StatusOfTheInboxTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.paths = create_test_paths(self.root)
        write_operational_corpus(self.root)
        (self.root / "state" / "inbox").mkdir(parents=True)

    def read_inbox_section(self, lines: str) -> dict:
        (self.root / "state" / "inbox" / "signals.jsonl").write_text(lines, encoding="utf-8")
        runtime = create_test_runtime(self.paths, run_process=create_corpus_double(CORPUS_OF_PROJECTS))
        return COMMAND.run(Namespace(), runtime)["inbox"]

    def test_should_list_each_scan_its_new_signals_name_with_their_count_and_the_age_of_the_oldest(self):
        # Arrange
        lines = (
            STALE_BRANCH_ON_ELM_RECORDED
            + LINT_ON_OAK_RECORDED_FIRST
            + OTHER_LINT_ON_OAK_RECORDED
            + LINT_ON_OAK_RECORDED_AGAIN
        )

        # Act
        inbox = self.read_inbox_section(lines)

        # Assert
        self.assertEqual(
            inbox,
            {
                "new_signals": 3,
                "scans": [
                    {"study": "corpus_lint_oak", "project": "oak", "signals": 2, "oldest_age_s": 7200},
                    {"study": "stale_branches_elm", "project": "elm", "signals": 1, "oldest_age_s": 900},
                ],
                "stalls": [],
            },
        )

    def test_should_leave_out_a_dismissed_scan_signal_and_a_signal_of_another_kind(self):
        # Arrange
        lines = NOTE_ON_OAK_RECORDED + WORKTREE_ON_OAK_RECORDED + WORKTREE_ON_OAK_DISMISSED

        # Act
        inbox = self.read_inbox_section(lines)

        # Assert
        self.assertEqual(inbox, {"new_signals": 1, "scans": [], "stalls": []})


class StatusTextTest(unittest.TestCase):
    def test_should_print_one_line_per_fact_of_the_home_document(self):
        # Act
        text = COMMAND.render_text(HOME)

        # Assert
        self.assertEqual(
            text,
            "project    elm, paused\n"
            "project    oak, active\n"
            "wave       oak_w2 of oak, wave.blocked, blocked on quota until 2026-10-19T10:00:00Z\n"
            "wave       elm_w1 of elm, wave.started\n"
            "inbox      1 new signals\n"
            "quota      over 5 hours: input_tokens 10, output_tokens 20, cache_creation_input_tokens 30,"
            " cache_read_input_tokens 40; 1 runs without usage\n"
            "last tick  2026-10-19T08:55:00Z, 2 actions applied in 120 ms\n"
            "study      debt, parked\n"
            "study      triage, due\n"
            "study      mine_transcripts, due\n"
            "study      corpus_lint_elm, due\n"
            "study      corpus_fmt_elm, due\n"
            "study      stale_branches_elm, due\n"
            "study      worktrees_elm, due\n"
            "study      corpus_lint_oak, due\n"
            "study      corpus_fmt_oak, due\n"
            "study      stale_branches_oak, due\n"
            "study      worktrees_oak, due",
        )

    def test_should_print_one_line_per_parked_order_after_the_studies(self):
        # Arrange
        home = {**HOME, "studies": [], "orders": [PARKED_NIGHTLY]}

        # Act
        text = COMMAND.render_text(home)

        # Assert
        self.assertEqual(text.splitlines()[-1], "order      nightly of oak, parked at 1-gate: the gate step failed")

    def test_should_print_one_line_per_scan_holding_new_signals_after_the_inbox(self):
        # Arrange
        document = {
            **HOME,
            "inbox": {
                "new_signals": 3,
                "scans": [
                    {"study": "corpus_lint_oak", "project": "oak", "signals": 2, "oldest_age_s": 7200},
                    {"study": "stale_branches_elm", "project": "elm", "signals": 1, "oldest_age_s": 900},
                ],
            },
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertIn(
            "\ninbox      3 new signals\n"
            "scan       corpus_lint_oak, 2 new signals, the oldest 2h\n"
            "scan       stale_branches_elm, 1 new signals, the oldest 15m\n"
            "quota      ",
            text,
        )

    def test_should_say_that_no_tick_ran(self):
        # Arrange
        document = {**HOME, "last_tick": None}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertIn("\nlast tick  never\n", text)

    def test_should_say_that_a_wave_parked_until_further_notice_has_no_resume_time(self):
        # Arrange
        document = {
            **HOME,
            "waves": [
                {
                    "wave": "elm_w1",
                    "project": "elm",
                    "branch": "integration/elm_w1",
                    "last_event": "wave.parked",
                    "tasks": 1,
                    "halt": {"reason": "forge_account", "resume_at": None},
                }
            ],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertIn("\nwave       elm_w1 of elm, wave.parked, parked on forge_account\n", text)
