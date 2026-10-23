import argparse
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from brigade.commands.ledger import COMMAND, ledger
from brigade.errors import UsageError

WAVE_STARTED = (
    '{"schema_version": 2, "ts": "2026-09-30T22:00:00Z", "event": "wave.started", "wave": "tidepool_w16",'
    ' "project": "tidepool", "branch": "integration/M4-tides", "tasks": ["T7"]}\n'
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.runtime = create_test_runtime(create_test_paths(Path(self.root.name)))
        self.ledger_directory = self.runtime.paths.state_root / "ledger"
        self.ledger_directory.mkdir(parents=True)

    def test_should_give_the_overview_of_the_journal_when_no_wave_and_no_project_is_asked(self):
        # Arrange
        (self.ledger_directory / "2026-10.jsonl").write_text("not a document\n")
        request = argparse.Namespace(wave=None, project=None, since=None)

        # Act
        document = ledger(request, self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "view": "overview",
                "events": {},
                "first": None,
                "last": None,
                "files": [str(self.ledger_directory / "2026-10.jsonl")],
                "runs": {"outcomes": {}, "error_classes": {}},
                "segments": {"outcomes": {}, "error_classes": {}},
                "skipped": [{"file": str(self.ledger_directory / "2026-10.jsonl"), "line": 1, "reason": "not JSON"}],
            },
        )

    def test_should_describe_the_wave_asked(self):
        # Arrange
        (self.ledger_directory / "2026-09.jsonl").write_text(WAVE_STARTED)
        request = argparse.Namespace(wave="tidepool_w16", project=None, since=None)

        # Act
        document = ledger(request, self.runtime)

        # Assert
        self.assertEqual(document["first"], "2026-09-30T22:00:00Z")

    def test_should_count_the_events_of_the_project_from_the_instant_since_names(self):
        # Arrange
        rows = [
            (None, None),
            (timedelta(days=2), "2026-10-17T09:00:00Z"),
            (date(2026, 10, 1), "2026-10-01T00:00:00Z"),
        ]
        for since, expected in rows:
            with self.subTest(since=since):
                request = argparse.Namespace(wave=None, project="app", since=since)

                # Act
                document = ledger(request, self.runtime)

                # Assert
                self.assertEqual(document["since"], expected)


class LedgerRequestTest(unittest.TestCase):
    def test_should_refuse_since_without_a_project(self):
        # Arrange
        options = argparse.Namespace(wave=None, project=None, since=timedelta(days=2))

        # Act
        with self.assertRaises(UsageError) as refusal:
            COMMAND.read_request(options)

        # Assert
        self.assertEqual(str(refusal.exception), "--since needs --project")

    def test_should_take_since_with_a_project(self):
        # Arrange
        options = argparse.Namespace(wave=None, project="app", since=timedelta(days=2))

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertEqual(request, argparse.Namespace(wave=None, project="app", since=timedelta(days=2)))


class LedgerExitCodeTest(unittest.TestCase):
    def test_should_exit_0_once_the_journal_is_read(self):
        # Arrange
        document = {"view": "project"}

        # Act
        exit_code = COMMAND.decide_exit_code(document)

        # Assert
        self.assertEqual(exit_code, 0)


class LedgerOverviewTextTest(unittest.TestCase):
    def test_should_count_the_events_runs_segments_and_error_classes_over_the_period(self):
        # Arrange
        document = {
            "view": "overview",
            "events": {"run.finished": 3, "wave.started": 1},
            "first": "2026-09-30T22:00:00Z",
            "last": "2026-10-01T01:00:00Z",
            "files": ["2026-09.jsonl", "2026-10.jsonl"],
            "skipped": [],
            "runs": {"outcomes": {"done": 2, "failed": 1}, "error_classes": {}},
            "segments": {"outcomes": {"done": 2, "failed": 1}, "error_classes": {"execution": 1}},
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "events: 4, from 2026-09-30T22:00:00Z to 2026-10-01T01:00:00Z\n"
            "files read: 2\n"
            "lines skipped: 0\n"
            "  run.finished  3\n"
            "  wave.started  1\n"
            "runs finished: 3, done 2, failed 1\n"
            "segments finished: 3, done 2, failed 1\n"
            "error classes of runs: none\n"
            "error classes of segments: execution 1",
        )

    def test_should_state_an_empty_journal_in_three_lines(self):
        # Arrange
        document = {
            "view": "overview",
            "events": {},
            "first": None,
            "last": None,
            "files": [],
            "skipped": [],
            "runs": {"outcomes": {}, "error_classes": {}},
            "segments": {"outcomes": {}, "error_classes": {}},
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "events: 0\nfiles read: 0\nlines skipped: 0")


class LedgerWaveTextTest(unittest.TestCase):
    def test_should_present_the_course_of_the_wave(self):
        # Arrange
        build_steps = {
            "runs": {"p50": 40, "p90": 52, "measured": 2, "partial": 0, "unmeasured": 0},
            "segments": {"p50": 40, "p90": 52, "measured": 2, "unmeasured": 0},
        }
        document = {
            "view": "wave",
            "wave": "tidepool_w16",
            "first": "2026-09-30T22:00:00Z",
            "last": "2026-10-01T02:30:00Z",
            "wall_time_ms": 16200000,
            "tasks": ["T7", "T8"],
            "pull_requests": [{"task": "T7", "pr": 42, "rounds": 2}],
            "steps": {"by_slot": {"build": build_steps}, "by_role": {}},
            "pauses": [
                {"paused_at": "2026-10-01T00:15:00Z", "resumed_at": "2026-10-01T01:15:00Z", "duration_ms": 3600000},
                {"paused_at": "2026-10-01T02:00:00Z", "resumed_at": None, "duration_ms": None},
            ],
            "paused_ms": 3600000,
            "hand_overs": [{"task": "T7", "role": "ada", "slot": "build", "segment": 2}],
            "parked": [],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "wave tidepool_w16: 2026-09-30T22:00:00Z to 2026-10-01T02:30:00Z, wall time 4h30m\n"
            "tasks: T7, T8\n"
            "pull requests: #42 T7 rounds 2\n"
            "steps by slot:\n"
            "  build\n"
            "    runs p50 40  p90 52  measured 2  partial 0  unmeasured 0\n"
            "    segments p50 40  p90 52  measured 2  unmeasured 0\n"
            "steps by role: none\n"
            "pauses: 2, 1h00m in all\n"
            "  2026-10-01T00:15:00Z to 2026-10-01T01:15:00Z  1h00m\n"
            "  2026-10-01T02:00:00Z, still paused\n"
            "hand-overs: T7 ada build segment 2\n"
            "parked: none",
        )


class LedgerProjectTextTest(unittest.TestCase):
    def test_should_count_what_the_project_delivered_since_the_instant(self):
        # Arrange
        document = {
            "view": "project",
            "project": "app",
            "since": "2026-10-01T00:00:00Z",
            "orders_done": {"build": 2},
            "waves_started": 1,
            "pull_requests_merged": 2,
            "signals_recorded": 0,
            "patterns_ratified": 0,
            "constraints_delivered": 0,
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "project app since 2026-10-01T00:00:00Z\n"
            "waves started: 1\n"
            "orders done: build 2\n"
            "pull requests merged: 2\n"
            "signals recorded: 0\n"
            "patterns ratified: 0\n"
            "constraints delivered: 0",
        )

    def test_should_count_no_order_done_as_0_over_the_whole_journal(self):
        # Arrange
        document = {
            "view": "project",
            "project": "app",
            "since": None,
            "orders_done": {},
            "waves_started": 0,
            "pull_requests_merged": 0,
            "signals_recorded": 0,
            "patterns_ratified": 0,
            "constraints_delivered": 0,
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "project app\n"
            "waves started: 0\n"
            "orders done: 0\n"
            "pull requests merged: 0\n"
            "signals recorded: 0\n"
            "patterns ratified: 0\n"
            "constraints delivered: 0",
        )
