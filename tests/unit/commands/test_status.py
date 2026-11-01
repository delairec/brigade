import dataclasses
import json
import tempfile
import unittest
from argparse import Namespace
from datetime import UTC, datetime
from pathlib import Path

from brigade.commands.status import COMMAND
from brigade.ledger.append_event import append_event
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.order_started import OrderStarted
from brigade.ledger.wave_closed import WaveClosed
from brigade.ledger.wave_paused import WavePaused
from brigade.ledger.wave_started import WaveStarted
from brigade.system.token_usage import TokenUsage
from tests.unit.commands.command_runtime import create_corpus_double, write_operational_corpus
from tests.unit.commands.inbox_lines import NOTE_ON_OAK_RECORDED, THREAD_DISMISSED, THREAD_RECORDED
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.ledger.create_run_finished import create_run_finished

OAK = (("PATH", "/srv/oak"), ("STATUS", "active"))
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
HOME = {
    "schema_version": 1,
    "projects": [{"name": "elm", "paused": True}, {"name": "oak", "paused": False}],
    "waves": [
        {
            "wave": "oak_w2",
            "project": "oak",
            "branch": "integration/oak_w2",
            "last_event": "wave.paused",
            "tasks": 2,
            "pause": {"reason": "quota", "resume_at": "2026-10-19T10:00:00Z"},
        },
        {
            "wave": "elm_w1",
            "project": "elm",
            "branch": "integration/elm_w1",
            "last_event": "wave.started",
            "tasks": 1,
            "pause": None,
        },
    ],
    "inbox": {"new_signals": 1, "scans": []},
    "quota": {
        "window_hours": 5,
        "usage": {
            "input_tokens": 10,
            "output_tokens": 20,
            "cache_creation_input_tokens": 30,
            "cache_read_input_tokens": 40,
        },
        "runs_without_usage": 1,
        "paused_waves": [{"wave": "oak_w2", "resume_at": "2026-10-19T10:00:00Z"}],
    },
    "last_tick": {"ts": "2026-10-19T08:55:00Z", "duration_ms": 120, "actions_applied": 2},
    "studies": [
        {
            "name": "debt",
            "status": "active",
            "every": "1d",
            "last_run": "20261019T080000Z-d1",
            "outcome": "parked",
            "due": False,
        },
        {"name": "triage", "status": "active", "every": "24h", "last_run": None, "outcome": None, "due": True},
        {"name": "corpus_lint_elm", "status": "active", "every": "24h", "last_run": None, "outcome": None, "due": True},
        {"name": "corpus_fmt_elm", "status": "active", "every": "24h", "last_run": None, "outcome": None, "due": True},
        {
            "name": "stale_branches_elm",
            "status": "active",
            "every": "24h",
            "last_run": None,
            "outcome": None,
            "due": True,
        },
        {"name": "worktrees_elm", "status": "active", "every": "24h", "last_run": None, "outcome": None, "due": True},
        {"name": "corpus_lint_oak", "status": "active", "every": "24h", "last_run": None, "outcome": None, "due": True},
        {"name": "corpus_fmt_oak", "status": "active", "every": "24h", "last_run": None, "outcome": None, "due": True},
        {
            "name": "stale_branches_oak",
            "status": "active",
            "every": "24h",
            "last_run": None,
            "outcome": None,
            "due": True,
        },
        {"name": "worktrees_oak", "status": "active", "every": "24h", "last_run": None, "outcome": None, "due": True},
    ],
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
            (at(7, 20), WavePaused(wave="oak_w2", reason="quota", resume_at="2026-10-19T10:00:00Z")),
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

    def test_should_leave_out_of_the_quota_a_wave_paused_on_another_reason(self):
        # Arrange
        self.write_machine()
        append_event(self.paths, at(8, 20), WavePaused(wave="elm_w1", reason="forge_account", resume_at=None))
        runtime = create_test_runtime(self.paths, run_process=create_corpus_double(CORPUS))

        # Act
        document = COMMAND.run(Namespace(), runtime)

        # Assert
        self.assertEqual(document["quota"]["paused_waves"], [{"wave": "oak_w2", "resume_at": "2026-10-19T10:00:00Z"}])


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
                    {"study": "corpus_lint_oak", "signals": 2, "oldest_age_s": 7200},
                    {"study": "stale_branches_elm", "signals": 1, "oldest_age_s": 900},
                ],
            },
        )

    def test_should_leave_out_a_dismissed_scan_signal_and_a_signal_of_another_kind(self):
        # Arrange
        lines = NOTE_ON_OAK_RECORDED + WORKTREE_ON_OAK_RECORDED + WORKTREE_ON_OAK_DISMISSED

        # Act
        inbox = self.read_inbox_section(lines)

        # Assert
        self.assertEqual(inbox, {"new_signals": 1, "scans": []})


class StatusTextTest(unittest.TestCase):
    def test_should_print_one_line_per_fact_of_the_home_document(self):
        # Act
        text = COMMAND.render_text(HOME)

        # Assert
        self.assertEqual(
            text,
            "project    elm, paused\n"
            "project    oak, active\n"
            "wave       oak_w2 of oak, wave.paused, paused on quota until 2026-10-19T10:00:00Z\n"
            "wave       elm_w1 of elm, wave.started\n"
            "inbox      1 new signals\n"
            "quota      over 5 hours: input_tokens 10, output_tokens 20, cache_creation_input_tokens 30,"
            " cache_read_input_tokens 40; 1 runs without usage\n"
            "last tick  2026-10-19T08:55:00Z, 2 actions applied in 120 ms\n"
            "study      debt, parked\n"
            "study      triage, due\n"
            "study      corpus_lint_elm, due\n"
            "study      corpus_fmt_elm, due\n"
            "study      stale_branches_elm, due\n"
            "study      worktrees_elm, due\n"
            "study      corpus_lint_oak, due\n"
            "study      corpus_fmt_oak, due\n"
            "study      stale_branches_oak, due\n"
            "study      worktrees_oak, due",
        )

    def test_should_print_one_line_per_scan_holding_new_signals_after_the_inbox(self):
        # Arrange
        document = {
            **HOME,
            "inbox": {
                "new_signals": 3,
                "scans": [
                    {"study": "corpus_lint_oak", "signals": 2, "oldest_age_s": 7200},
                    {"study": "stale_branches_elm", "signals": 1, "oldest_age_s": 900},
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

    def test_should_say_that_a_wave_paused_until_further_notice_has_no_resume_time(self):
        # Arrange
        document = {
            **HOME,
            "waves": [
                {
                    "wave": "elm_w1",
                    "project": "elm",
                    "branch": "integration/elm_w1",
                    "last_event": "wave.paused",
                    "tasks": 1,
                    "pause": {"reason": "forge_account", "resume_at": None},
                }
            ],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertIn("\nwave       elm_w1 of elm, wave.paused, paused on forge_account\n", text)
