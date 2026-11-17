import argparse
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from brigade.commands.ledger import COMMAND, ledger

WAVE_STARTED = (
    '{"schema_version": 2, "ts": "2026-09-30T22:00:00Z", "event": "wave.started", "wave": "tidepool_w16",'
    ' "project": "tidepool", "branch": "integration/M4-tides", "tasks": ["T7"]}\n'
)
TASK_RUN_EARLIER = (
    '{"schema_version": 3, "ts": "2026-10-01T09:00:00Z", "event": "run.finished", "run": "r1", "segment": 1,'
    ' "procedure": "build-task", "slot": "build", "role": "ada", "client": "claude-code", "project": "tidepool",'
    ' "session": null, "main_turns": 40, "total_turns": null, "duration_ms": 60000, "usage": null, "outcome": "done",'
    ' "error_class": null, "exit": 0, "wave": "tidepool_w16", "task": "TP1", "nulls": {}, "cost_usd": 4.0}\n'
)
TASK_RUN_LATER = (
    '{"schema_version": 3, "ts": "2026-10-06T09:00:00Z", "event": "run.finished", "run": "r2", "segment": 1,'
    ' "procedure": "build-task", "slot": "build", "role": "ada", "client": "claude-code", "project": "tidepool",'
    ' "session": null, "main_turns": 30, "total_turns": null, "duration_ms": 120000, "usage": null, "outcome": "done",'
    ' "error_class": null, "exit": 0, "wave": "tidepool_w16", "task": "TP1", "nulls": {}, "cost_usd": 2.5}\n'
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

    def test_should_give_the_overview_of_the_ledger_when_no_wave_and_no_project_is_asked(self):
        # Arrange
        (self.ledger_directory / "2026-10.jsonl").write_text("not a document\n")
        request = argparse.Namespace(wave=None, task=None, project=None, since=None)

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
                "waves_started": {},
                "since": None,
                "skipped": [{"file": str(self.ledger_directory / "2026-10.jsonl"), "line": 1, "reason": "not JSON"}],
            },
        )

    def test_should_describe_the_wave_asked(self):
        # Arrange
        (self.ledger_directory / "2026-09.jsonl").write_text(WAVE_STARTED)
        request = argparse.Namespace(wave="tidepool_w16", task=None, project=None, since=None)

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
                request = argparse.Namespace(wave=None, task=None, project="app", since=since)

                # Act
                document = ledger(request, self.runtime)

                # Assert
                self.assertEqual(document["since"], expected)


class LedgerSinceTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.runtime = create_test_runtime(create_test_paths(Path(self.root.name)))
        ledger_directory = self.runtime.paths.state_root / "ledger"
        ledger_directory.mkdir(parents=True)
        (ledger_directory / "2026-10.jsonl").write_text(TASK_RUN_EARLIER + TASK_RUN_LATER)

    def test_should_read_the_overview_from_the_instant_since_names(self):
        # Arrange
        request = argparse.Namespace(wave=None, task=None, project=None, since=date(2026, 10, 5))

        # Act
        document = ledger(request, self.runtime)

        # Assert
        self.assertEqual(document["events"], {"run.finished": 1})

    def test_should_read_the_runs_of_the_task_from_the_instant_since_names(self):
        # Arrange
        request = argparse.Namespace(wave=None, task="TP1", project=None, since=date(2026, 10, 5))

        # Act
        document = ledger(request, self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "view": "task",
                "task": "TP1",
                "runs": [
                    {
                        "run": "r2",
                        "finished_at": "2026-10-06T09:00:00Z",
                        "slot": "build",
                        "outcome": "done",
                        "turns": 30,
                        "partial": False,
                        "duration_ms": 120000,
                        "cost_usd": 2.5,
                    }
                ],
                "since": "2026-10-05T00:00:00Z",
                "skipped": [],
            },
        )

    def test_should_read_the_wave_from_the_instant_since_names(self):
        # Arrange
        request = argparse.Namespace(wave="tidepool_w16", task=None, project=None, since=date(2026, 10, 5))

        # Act
        document = ledger(request, self.runtime)

        # Assert
        self.assertEqual(document["first"], "2026-10-06T09:00:00Z")


class LedgerOfNoLedgerTest(unittest.TestCase):
    def test_should_give_an_empty_overview_when_the_ledger_directory_does_not_exist(self):
        # Arrange
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        runtime = create_test_runtime(create_test_paths(Path(directory.name)))
        request = argparse.Namespace(wave=None, task=None, project=None, since=None)

        # Act
        document = ledger(request, runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "view": "overview",
                "events": {},
                "first": None,
                "last": None,
                "files": [],
                "skipped": [],
                "runs": {"outcomes": {}, "error_classes": {}},
                "segments": {"outcomes": {}, "error_classes": {}},
                "waves_started": {},
                "since": None,
            },
        )


class LedgerRequestTest(unittest.TestCase):
    def test_should_take_since_with_every_view(self):
        for wave, task, project in [(None, None, None), ("w1", None, None), (None, "TP1", None), (None, None, "app")]:
            with self.subTest(wave=wave, task=task, project=project):
                # Arrange
                options = argparse.Namespace(wave=wave, task=task, project=project, since=timedelta(days=2))

                # Act
                request = COMMAND.read_request(options)

                # Assert
                self.assertEqual(
                    request, argparse.Namespace(wave=wave, task=task, project=project, since=timedelta(days=2))
                )


class LedgerExitCodeTest(unittest.TestCase):
    def test_should_exit_0_once_the_ledger_is_read(self):
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

    def test_should_state_an_empty_ledger_in_three_lines(self):
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

    def test_should_count_the_runs_apart_from_their_segments(self):
        # Arrange
        document = {
            "view": "overview",
            "events": {"run.finished": 3},
            "first": "2026-10-01T09:00:00Z",
            "last": "2026-10-02T09:00:00Z",
            "files": ["2026-10.jsonl"],
            "skipped": [],
            "runs": {"outcomes": {"done": 2}, "error_classes": {}},
            "segments": {"outcomes": {"done": 2, "wall_limit": 1}, "error_classes": {}},
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "events: 3, from 2026-10-01T09:00:00Z to 2026-10-02T09:00:00Z\n"
            "files read: 1\n"
            "lines skipped: 0\n"
            "  run.finished  3\n"
            "runs finished: 2, done 2\n"
            "segments finished: 3, done 2, wall_limit 1",
        )


class LedgerTaskTextTest(unittest.TestCase):
    def test_should_present_each_run_of_the_task(self):
        # Arrange
        document = {
            "view": "task",
            "task": "TP1",
            "runs": [
                {
                    "run": "r1",
                    "finished_at": "2026-10-06T09:00:00Z",
                    "slot": "build",
                    "outcome": "done",
                    "turns": 30,
                    "partial": False,
                    "duration_ms": 120000,
                    "cost_usd": 2.5,
                },
                {
                    "run": "r2",
                    "finished_at": "2026-10-06T10:00:00Z",
                    "slot": "build",
                    "outcome": "budget_reached",
                    "turns": 75,
                    "partial": True,
                    "duration_ms": 3720000,
                    "cost_usd": None,
                },
                {
                    "run": "r3",
                    "finished_at": "2026-10-06T11:00:00Z",
                    "slot": "verify",
                    "outcome": "failed",
                    "turns": None,
                    "partial": False,
                    "duration_ms": None,
                    "cost_usd": None,
                },
            ],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "task TP1: 3 runs\n"
            "  r1  2026-10-06T09:00:00Z  build  done  turns 30  duration 0h02m  cost 2.50 USD\n"
            "  r2  2026-10-06T10:00:00Z  build  budget_reached  turns 75 partial  duration 1h02m  cost -\n"
            "  r3  2026-10-06T11:00:00Z  verify  failed  turns -  duration -  cost -",
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

    def test_should_count_no_order_done_as_0_over_the_whole_ledger(self):
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
