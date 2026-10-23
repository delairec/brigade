import json
import tempfile
import unittest
from pathlib import Path

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine

WAVE_SEPTEMBER_LINES = (
    '{"schema_version": 2, "ts": "2026-09-30T22:00:00Z", "event": "wave.started", "wave": "tidepool_w16",'
    ' "project": "tidepool", "branch": "integration/M1", "tasks": ["T1"]}\n'
    '{"schema_version": 2, "ts": "2026-09-30T22:10:00Z", "event": "run.finished", "wave": "tidepool_w16", "task": "TP146",'
    ' "run": "20261001T000000Z-a00001", "client": "claude-code", "project": "tidepool", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "failed",'
    ' "error_class": "rate_limit", "main_steps": 50, "total_steps": null}\n'
    '{"schema_version": 1, "ts": "2026-09-30T22:15:00Z", "event": "wave.paused", "wave": "tidepool_w16", "reason": "quota", "resume_at": null}\n'
)
WAVE_OCTOBER_LINES = (
    '{"schema_version": 1, "ts": "2026-10-01T00:15:00Z", "event": "wave.resumed", "wave": "tidepool_w16", "reason": "quota"}\n'
    '{"schema_version": 2, "ts": "2026-10-01T00:40:00Z", "event": "run.finished", "wave": "tidepool_w16", "task": "TP146",'
    ' "run": "20261001T000000Z-a00001", "client": "claude-code", "project": "tidepool", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 2, "outcome": "done",'
    ' "error_class": null, "main_steps": 30, "total_steps": null}\n'
    '{"schema_version": 1, "ts": "2026-10-01T00:41\n'
    '{"schema_version": 2, "ts": "2026-10-01T00:50:00Z", "event": "run.finished", "wave": "tidepool_w16", "task": "TP147",'
    ' "run": "20261001T000000Z-a00002", "client": "claude-code", "project": "tidepool", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_steps": null, "total_steps": null}\n'
    '{"schema_version": 2, "ts": "2026-10-01T01:00:00Z", "event": "run.finished", "wave": "tidepool_w16", "task": "TP146",'
    ' "run": "20261001T000000Z-a00003", "client": "claude-code", "project": "tidepool", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "awawa-pr-review", "role": "remi", "slot": "review", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_steps": 12, "total_steps": null}\n'
    '{"schema_version": 1, "ts": "2026-10-01T01:30:00Z", "event": "pr.merged", "project": "tidepool", "wave": "tidepool_w16",'
    ' "task": "TP146", "pr": 291, "rounds": 1, "login": "tidepool-cli"}\n'
    '{"schema_version": 1, "ts": "2026-10-01T01:40:00Z", "event": "task.parked", "wave": "tidepool_w16", "task": "TP147",'
    ' "reason": "blocked", "blockers": ["OPEN_QUESTION.Undecided"]}\n'
    '{"schema_version": 2, "ts": "2026-10-01T02:00:00Z", "event": "run.finished", "wave": "tidepool_w17", "task": "TP150",'
    ' "run": "20261001T000000Z-a00004", "client": "claude-code", "project": "tidepool", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_steps": 20, "total_steps": null}\n'
)
BUDGET_LINES = (
    '{"schema_version": 2, "ts": "2026-10-01T08:00:00Z", "event": "run.finished", "wave": "tidepool_w16", "task": "TP146",'
    ' "run": "20261001T000000Z-b00001", "client": "claude-code", "project": "tidepool", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_steps": 90, "total_steps": null}\n'
    '{"schema_version": 2, "ts": "2026-10-01T09:00:00Z", "event": "run.finished", "wave": "tidepool_w16", "task": "TP147",'
    ' "run": "20261001T000000Z-b00002", "client": "claude-code", "project": "tidepool", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_steps": 80, "total_steps": null}\n'
    '{"schema_version": 2, "ts": "2026-10-01T10:00:00Z", "event": "run.finished", "wave": "tidepool_w16", "task": "TP146",'
    ' "run": "20261001T000000Z-b00003", "client": "claude-code", "project": "tidepool", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "awawa-pr-review", "role": "remi", "slot": "review", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_steps": 12, "total_steps": null}\n'
    '{"schema_version": 2, "ts": "2026-10-01T11:00:00Z", "event": "run.finished", "wave": "tidepool_w16", "task": "TP148",'
    ' "run": "20261001T000000Z-b00004", "client": "claude-code", "project": "tidepool", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_steps": null, "total_steps": null}\n'
    '{"schema_version": 2, "ts": "2026-10-01T12:00:00Z", "event": "run.finished", "wave": "tidepool_w16", "task": "TP149",'
    ' "run": "20261001T000000Z-b00005", "client": "claude-code", "project": "tidepool", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_steps": 10, "total_steps": null}\n'
    '{"schema_version": 2, "ts": "2026-10-01T13:00:00Z", "event": "run.finished", "wave": "tidepool_w16", "task": "TP147",'
    ' "run": "20261001T000000Z-b00006", "client": "claude-code", "project": "tidepool", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "awawa-pr-review", "role": "remi", "slot": "review", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_steps": 8, "total_steps": null}\n'
    '{"schema_version": 2, "ts": "2026-10-01T14:00:00Z", "event": "run.finished", "wave": "tidepool_w16", "task": "TP150",'
    ' "run": "20261001T000000Z-b00007", "client": "claude-code", "project": "tidepool", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_steps": 20, "total_steps": null}\n'
    '{"schema_version": 2, "ts": "2026-10-01T15:00:00Z", "event": "run.finished", "wave": "tidepool_w16", "task": "TP151",'
    ' "run": "20261001T000000Z-b00008", "client": "claude-code", "project": "tidepool", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_steps": 30, "total_steps": null}\n'
)
COMPARISON_LINES = (
    '{"schema_version": 2, "ts": "2026-10-01T08:00:00Z", "event": "wave.started", "wave": "tidepool_w16",'
    ' "project": "tidepool", "branch": "integration/M1", "tasks": ["T1"]}\n'
    '{"schema_version": 2, "ts": "2026-10-01T09:00:00Z", "event": "run.finished", "wave": "tidepool_w16", "task": "TP146",'
    ' "run": "20261001T000000Z-c00001", "client": "claude-code", "project": "tidepool", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_steps": 40, "total_steps": null, "steps_to_first_edit": 12}\n'
    '{"schema_version": 2, "ts": "2026-10-02T09:00:00Z", "event": "run.finished", "wave": "tidepool_w16", "task": "TP147",'
    ' "run": "20261001T000000Z-c00002", "client": "claude-code", "project": "tidepool", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_steps": 60, "total_steps": null}\n'
    '{"schema_version": 2, "ts": "2026-10-02T23:59:59Z", "event": "run.finished", "wave": "tidepool_w16", "task": "TP148",'
    ' "run": "20261001T000000Z-c00003", "client": "claude-code", "project": "tidepool", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_steps": null, "total_steps": null}\n'
    '{"schema_version": 2, "ts": "2026-10-03T00:00:00Z", "event": "run.finished", "wave": "tidepool_w17", "task": "TP150",'
    ' "run": "20261001T000000Z-c00004", "client": "claude-code", "project": "tidepool", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_steps": 20, "total_steps": null, "steps_to_first_edit": 4, "oversized_output_steps": 1}\n'
    '{"schema_version": 2, "ts": "2026-10-04T09:00:00Z", "event": "run.finished", "wave": "tidepool_w17", "task": "TP151",'
    ' "run": "20261001T000000Z-c00005", "client": "claude-code", "project": "tidepool", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_steps": 30, "total_steps": null}\n'
)
PROJECT_SEPTEMBER_LINES = (
    '{"schema_version": 2, "ts": "2026-09-20T08:00:00Z", "event": "wave.started", "wave": "tidepool_w15",'
    ' "project": "tidepool", "branch": "integration/M1", "tasks": ["T1"]}\n'
)
PROJECT_OCTOBER_LINES = (
    '{"schema_version": 2, "ts": "2026-10-02T08:00:00Z", "event": "wave.started", "wave": "tidepool_w16",'
    ' "project": "tidepool", "branch": "integration/M1", "tasks": ["T1"]}\n'
    '{"schema_version": 2, "ts": "2026-10-02T08:00:00Z", "event": "wave.started", "wave": "oboe_w3",'
    ' "project": "oboe", "branch": "integration/M1", "tasks": ["T1"]}\n'
    '{"schema_version": 1, "ts": "2026-10-02T09:00:00Z", "event": "order.done", "project": "tidepool",'
    ' "kind": "study"}\n'
    '{"schema_version": 1, "ts": "2026-10-02T10:00:00Z", "event": "order.done", "project": "tidepool",'
    ' "kind": "intake"}\n'
    '{"schema_version": 1, "ts": "2026-10-02T11:00:00Z", "event": "order.done", "project": "tidepool",'
    ' "kind": "study"}\n'
    '{"schema_version": 1, "ts": "2026-10-02T11:00:00Z", "event": "order.done", "project": "oboe", "kind": "study"}\n'
    '{"schema_version": 1, "ts": "2026-10-02T12:00:00Z", "event": "pr.merged", "project": "tidepool", "wave": "tidepool_w16",'
    ' "task": "TP146", "pr": 291, "rounds": 1, "login": "tidepool-cli"}\n'
    '{"schema_version": 1, "ts": "2026-10-02T13:00:00Z", "event": "signal.recorded", "signal": "budget_reached",'
    ' "project": "tidepool", "procedure": "deliver", "run": "20261002T130000Z-a00002", "segment": 1, "budget": 40}\n'
    '{"schema_version": 1, "ts": "2026-10-02T14:00:00Z", "event": "pattern.ratified", "project": "tidepool"}\n'
    '{"schema_version": 1, "ts": "2026-10-02T15:00:00Z", "event": "constraint.delivered", "project": "tidepool"}\n'
)
OLD_WAVE_LINES = (
    '{"schema_version": 2, "ts": "2020-01-01T08:00:00Z", "event": "wave.started", "wave": "tidepool_w1",'
    ' "project": "tidepool", "branch": "integration/M1", "tasks": ["T1"]}\n'
)
REPEATED_PAUSE_LINES = (
    '{"schema_version": 2, "ts": "2026-10-01T08:00:00Z", "event": "wave.started", "wave": "tidepool_w18",'
    ' "project": "tidepool", "branch": "integration/M1", "tasks": ["T1"]}\n'
    '{"schema_version": 1, "ts": "2026-10-01T09:00:00Z", "event": "wave.paused", "wave": "tidepool_w18", "reason": "quota", "resume_at": null}\n'
    '{"schema_version": 1, "ts": "2026-10-01T09:30:00Z", "event": "wave.paused", "wave": "tidepool_w18", "reason": "quota", "resume_at": null}\n'
    '{"schema_version": 1, "ts": "2026-10-01T10:00:00Z", "event": "wave.resumed", "wave": "tidepool_w18", "reason": "quota"}\n'
    '{"schema_version": 1, "ts": "2026-10-01T10:30:00Z", "event": "wave.resumed", "wave": "tidepool_w18", "reason": "quota"}\n'
)
UNMEASURED_RUN_LINES = (
    '{"schema_version": 2, "ts": "2026-10-01T08:00:00Z", "event": "run.finished", "wave": "tidepool_w16", "task": "TP146",'
    ' "run": "20261001T000000Z-a00001", "client": "claude-code", "project": "tidepool", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "awawa-study", "role": "dora", "slot": "study", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_steps": null, "total_steps": null}\n'
)
RUN_OF_TWO_SEGMENTS_LINES = (
    '{"schema_version": 2, "ts": "2026-10-02T09:00:00Z", "event": "run.finished", "wave": "tidepool_w20", "task": "TP160",'
    ' "run": "20261002T080000Z-d00001", "client": "claude-code", "project": "tidepool", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": null, "nulls": {},'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "wall_limit",'
    ' "error_class": null, "main_steps": null, "total_steps": null}\n'
    '{"schema_version": 2, "ts": "2026-10-02T12:00:00Z", "event": "run.finished", "wave": "tidepool_w20", "task": "TP161",'
    ' "run": "20261002T110000Z-d00002", "client": "claude-code", "project": "tidepool", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_steps": 20, "total_steps": null, "steps_to_first_edit": 6}\n'
    '{"schema_version": 2, "ts": "2026-10-03T09:00:00Z", "event": "run.finished", "wave": "tidepool_w20", "task": "TP160",'
    ' "run": "20261002T080000Z-d00001", "client": "claude-code", "project": "tidepool", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 2, "outcome": "done",'
    ' "error_class": null, "main_steps": 30, "total_steps": null, "steps_to_first_edit": 4, "oversized_output_steps": 1}\n'
)


class LedgerTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.machine = TemporaryMachine(Path(self.root.name).resolve())
        self.ledger = self.machine.state_home / "brigade" / "ledger"

    def tearDown(self):
        self.root.cleanup()

    def write_ledger(self, month: str, lines: str) -> Path:
        ledger_file = self.ledger / f"{month}.jsonl"
        ledger_file.parent.mkdir(parents=True, exist_ok=True)
        ledger_file.write_text(lines)
        return ledger_file

    def run_ledger(self, *arguments: str):
        return self.machine.run_brigade(CLONE_ENTRY_POINT, "ledger", *arguments)


class BrigadeLedgerOnAWaveStartedOfTheFirstVersionTest(LedgerTestCase):
    def test_should_list_the_line_under_skipped_without_reading_it(self):
        # Arrange
        october = self.write_ledger(
            "2026-10",
            '{"schema_version": 1, "ts": "2026-10-02T08:00:00Z", "event": "wave.started", "wave": "M1",'
            ' "project": "tidepool"}\n',
        )

        # Act
        completed = self.run_ledger("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["events"], {})
        self.assertEqual(
            json.loads(completed.stdout)["skipped"],
            [{"file": str(october), "line": 1, "reason": "schema_version is 1, not one of 2"}],
        )


class BrigadeLedgerOverviewTest(LedgerTestCase):
    def setUp(self):
        super().setUp()
        self.september = self.write_ledger("2026-09", WAVE_SEPTEMBER_LINES)
        self.october = self.write_ledger("2026-10", WAVE_OCTOBER_LINES)

    def test_should_count_the_events_and_the_runs_finished_of_every_monthly_file(self):
        # Act
        completed = self.run_ledger("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "view": "overview",
                "events": {
                    "pr.merged": 1,
                    "run.finished": 5,
                    "task.parked": 1,
                    "wave.paused": 1,
                    "wave.resumed": 1,
                    "wave.started": 1,
                },
                "first": "2026-09-30T22:00:00Z",
                "last": "2026-10-01T02:00:00Z",
                "files": [str(self.september), str(self.october)],
                "skipped": [{"file": str(self.october), "line": 3, "reason": "not JSON"}],
                "runs": {"outcomes": {"done": 4}, "error_classes": {}},
                "segments": {"outcomes": {"done": 4, "failed": 1}, "error_classes": {"rate_limit": 1}},
            },
        )

    def test_should_report_the_skipped_line_on_stderr_and_still_exit_0(self):
        # Act
        completed = self.run_ledger()

        # Assert
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stderr, f"brigade ledger: skipped {self.october}:3: not JSON\n")

    def test_should_print_the_overview_as_text(self):
        # Act
        completed = self.run_ledger()

        # Assert
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "events: 10, from 2026-09-30T22:00:00Z to 2026-10-01T02:00:00Z",
                "files read: 2",
                "lines skipped: 1",
                "  pr.merged     1",
                "  run.finished  5",
                "  task.parked   1",
                "  wave.paused   1",
                "  wave.resumed  1",
                "  wave.started  1",
                "runs finished: 4, done 4",
                "segments finished: 5, done 4, failed 1",
                "error classes of runs: none",
                "error classes of segments: rate_limit 1",
            ],
        )


class BrigadeLedgerOverviewWithNoLedgerTest(LedgerTestCase):
    def test_should_report_zero_events_and_exit_0(self):
        # Act
        completed = self.run_ledger("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
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
            },
        )

    def test_should_print_zero_events_as_text(self):
        # Act
        completed = self.run_ledger()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.splitlines(), ["events: 0", "files read: 0", "lines skipped: 0"])


class BrigadeLedgerWaveTest(LedgerTestCase):
    def setUp(self):
        super().setUp()
        self.write_ledger("2026-09", WAVE_SEPTEMBER_LINES)
        self.october = self.write_ledger("2026-10", WAVE_OCTOBER_LINES)

    def test_should_describe_the_tasks_steps_pauses_hand_overs_and_parked_tasks_of_the_wave(self):
        # Act
        completed = self.run_ledger("--wave", "tidepool_w16", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "view": "wave",
                "wave": "tidepool_w16",
                "first": "2026-09-30T22:00:00Z",
                "last": "2026-10-01T01:40:00Z",
                "wall_time_ms": 13200000,
                "tasks": ["TP146", "TP147"],
                "pull_requests": [{"task": "TP146", "pr": 291, "rounds": 1}],
                "steps": {
                    "by_slot": {
                        "build": {
                            "runs": {"measured": 1, "partial": 0, "unmeasured": 1, "p50": 80, "p90": 80},
                            "segments": {"measured": 2, "unmeasured": 1, "p50": 30, "p90": 50},
                        },
                        "review": {
                            "runs": {"measured": 1, "partial": 0, "unmeasured": 0, "p50": 12, "p90": 12},
                            "segments": {"measured": 1, "unmeasured": 0, "p50": 12, "p90": 12},
                        },
                    },
                    "by_role": {
                        "builder": {
                            "runs": {"measured": 1, "partial": 0, "unmeasured": 1, "p50": 80, "p90": 80},
                            "segments": {"measured": 2, "unmeasured": 1, "p50": 30, "p90": 50},
                        },
                        "remi": {
                            "runs": {"measured": 1, "partial": 0, "unmeasured": 0, "p50": 12, "p90": 12},
                            "segments": {"measured": 1, "unmeasured": 0, "p50": 12, "p90": 12},
                        },
                    },
                },
                "pauses": [
                    {"paused_at": "2026-09-30T22:15:00Z", "resumed_at": "2026-10-01T00:15:00Z", "duration_ms": 7200000}
                ],
                "paused_ms": 7200000,
                "hand_overs": [{"task": "TP146", "role": "builder", "slot": "build", "segment": 2}],
                "parked": ["TP147"],
                "skipped": [{"file": str(self.october), "line": 3, "reason": "not JSON"}],
            },
        )

    def test_should_print_the_wave_as_text(self):
        # Act
        completed = self.run_ledger("--wave", "tidepool_w16")

        # Assert
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "wave tidepool_w16: 2026-09-30T22:00:00Z to 2026-10-01T01:40:00Z, wall time 3h40m",
                "tasks: TP146, TP147",
                "pull requests: #291 TP146 rounds 1",
                "steps by slot:",
                "  build",
                "    runs p50 80  p90 80  measured 1  partial 0  unmeasured 1",
                "    segments p50 30  p90 50  measured 2  unmeasured 1",
                "  review",
                "    runs p50 12  p90 12  measured 1  partial 0  unmeasured 0",
                "    segments p50 12  p90 12  measured 1  unmeasured 0",
                "steps by role:",
                "  builder",
                "    runs p50 80  p90 80  measured 1  partial 0  unmeasured 1",
                "    segments p50 30  p90 50  measured 2  unmeasured 1",
                "  remi",
                "    runs p50 12  p90 12  measured 1  partial 0  unmeasured 0",
                "    segments p50 12  p90 12  measured 1  unmeasured 0",
                "pauses: 1, 2h00m in all",
                "  2026-09-30T22:15:00Z to 2026-10-01T00:15:00Z  2h00m",
                "hand-overs: TP146 builder build segment 2",
                "parked: TP147",
            ],
        )


class BrigadeLedgerWaveStillPausedTest(LedgerTestCase):
    def test_should_leave_the_open_pause_out_of_the_total(self):
        # Arrange
        self.write_ledger("2026-09", WAVE_SEPTEMBER_LINES)

        # Act
        completed = self.run_ledger("--wave", "tidepool_w16", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        document = json.loads(completed.stdout)
        self.assertEqual(
            document["pauses"], [{"paused_at": "2026-09-30T22:15:00Z", "resumed_at": None, "duration_ms": None}]
        )
        self.assertEqual(document["paused_ms"], 0)

    def test_should_print_the_open_pause_as_text(self):
        # Arrange
        self.write_ledger("2026-09", WAVE_SEPTEMBER_LINES)

        # Act
        completed = self.run_ledger("--wave", "tidepool_w16")

        # Assert
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "wave tidepool_w16: 2026-09-30T22:00:00Z to 2026-09-30T22:15:00Z, wall time 0h15m",
                "tasks: TP146",
                "pull requests: none",
                "steps by slot:",
                "  build",
                "    runs p50 50  p90 50  measured 1  partial 0  unmeasured 0",
                "    segments p50 50  p90 50  measured 1  unmeasured 0",
                "steps by role:",
                "  builder",
                "    runs p50 50  p90 50  measured 1  partial 0  unmeasured 0",
                "    segments p50 50  p90 50  measured 1  unmeasured 0",
                "pauses: 1, 0h00m in all",
                "  2026-09-30T22:15:00Z, still paused",
                "hand-overs: none",
                "parked: none",
            ],
        )


class BrigadeLedgerWaveWithARepeatedPauseTest(LedgerTestCase):
    def setUp(self):
        super().setUp()
        self.write_ledger("2026-10", REPEATED_PAUSE_LINES)

    def test_should_pair_the_first_pause_with_the_first_resume_that_follows_it(self):
        # Act
        completed = self.run_ledger("--wave", "tidepool_w18", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        document = json.loads(completed.stdout)
        self.assertEqual(
            document["pauses"],
            [{"paused_at": "2026-10-01T09:00:00Z", "resumed_at": "2026-10-01T10:00:00Z", "duration_ms": 3600000}],
        )
        self.assertEqual(document["paused_ms"], 3600000)

    def test_should_print_none_for_what_the_wave_did_not_do(self):
        # Act
        completed = self.run_ledger("--wave", "tidepool_w18")

        # Assert
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "wave tidepool_w18: 2026-10-01T08:00:00Z to 2026-10-01T10:30:00Z, wall time 2h30m",
                "tasks: none",
                "pull requests: none",
                "steps by slot: none",
                "steps by role: none",
                "pauses: 1, 1h00m in all",
                "  2026-10-01T09:00:00Z to 2026-10-01T10:00:00Z  1h00m",
                "hand-overs: none",
                "parked: none",
            ],
        )


class BrigadeLedgerWaveUnknownTest(LedgerTestCase):
    def test_should_exit_1_naming_the_wave(self):
        # Arrange
        self.write_ledger("2026-09", WAVE_SEPTEMBER_LINES)

        # Act
        completed = self.run_ledger("--wave", "tidepool_w99", "--json")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(completed.stderr, "brigade ledger: no event names the wave tidepool_w99\n")


class BrigadeLedgerProjectTest(LedgerTestCase):
    def setUp(self):
        super().setUp()
        self.write_ledger("2026-09", PROJECT_SEPTEMBER_LINES)
        self.write_ledger("2026-10", PROJECT_OCTOBER_LINES)

    def test_should_count_the_project_events_of_the_whole_ledger(self):
        # Act
        completed = self.run_ledger("--project", "tidepool", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "view": "project",
                "project": "tidepool",
                "since": None,
                "waves_started": 2,
                "orders_done": {"intake": 1, "study": 2},
                "pull_requests_merged": 1,
                "signals_recorded": 1,
                "patterns_ratified": 1,
                "constraints_delivered": 1,
                "skipped": [],
            },
        )

    def test_should_count_from_the_start_of_the_day_given_in_utc(self):
        # Act
        completed = self.run_ledger("--project", "tidepool", "--since", "2026-10-01", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        document = json.loads(completed.stdout)
        self.assertEqual(document["since"], "2026-10-01T00:00:00Z")
        self.assertEqual(document["waves_started"], 1)

    def test_should_print_the_counts_as_text(self):
        # Act
        completed = self.run_ledger("--project", "tidepool", "--since", "2026-10-01")

        # Assert
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "project tidepool since 2026-10-01T00:00:00Z",
                "waves started: 1",
                "orders done: intake 1, study 2",
                "pull requests merged: 1",
                "signals recorded: 1",
                "patterns ratified: 1",
                "constraints delivered: 1",
            ],
        )


class BrigadeLedgerProjectWithNoEventTest(LedgerTestCase):
    def test_should_print_zero_counts_as_text(self):
        # Act
        completed = self.run_ledger("--project", "tidepool")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "project tidepool",
                "waves started: 0",
                "orders done: 0",
                "pull requests merged: 0",
                "signals recorded: 0",
                "patterns ratified: 0",
                "constraints delivered: 0",
            ],
        )


class BrigadeLedgerProjectSinceADayCountTest(LedgerTestCase):
    def test_should_count_the_days_back_from_now(self):
        # Arrange
        rows = [("1d", 0), ("36500d", 1)]
        for since, expected_waves_started in rows:
            with self.subTest(since=since):
                # Arrange
                self.write_ledger("2020-01", OLD_WAVE_LINES)

                # Act
                completed = self.run_ledger("--project", "tidepool", "--since", since, "--json")

                # Assert
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(json.loads(completed.stdout)["waves_started"], expected_waves_started)


class BrigadeLedgerBudgetsTest(LedgerTestCase):
    def setUp(self):
        super().setUp()
        self.write_ledger("2026-10", BUDGET_LINES)

    def test_should_give_p50_and_p90_steps_per_procedure_over_the_last_20_runs(self):
        # Act
        completed = self.run_ledger("budgets", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "last": 20,
                "procedures": {
                    "awawa-pr-review": {
                        "runs": {"measured": 2, "partial": 0, "unmeasured": 0, "p50": 8, "p90": 12},
                        "segments": {"measured": 2, "unmeasured": 0, "p50": 8, "p90": 12},
                        "estimate": True,
                    },
                    "awawa-task": {
                        "runs": {"measured": 5, "partial": 0, "unmeasured": 1, "p50": 30, "p90": 90},
                        "segments": {"measured": 5, "unmeasured": 1, "p50": 30, "p90": 90},
                        "estimate": False,
                    },
                },
                "skipped": [],
            },
        )

    def test_should_keep_the_last_runs_of_each_procedure_only(self):
        # Act
        completed = self.run_ledger("budgets", "--last", "3", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["procedures"]["awawa-task"],
            {
                "runs": {"measured": 3, "partial": 0, "unmeasured": 0, "p50": 20, "p90": 30},
                "segments": {"measured": 3, "unmeasured": 0, "p50": 20, "p90": 30},
                "estimate": True,
            },
        )

    def test_should_print_the_budgets_as_text(self):
        # Act
        completed = self.run_ledger("budgets")

        # Assert
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "steps over the last 20 runs finished of each procedure:",
                "  awawa-pr-review  estimate",
                "    runs p50 8  p90 12  measured 2  partial 0  unmeasured 0",
                "    segments p50 8  p90 12  measured 2  unmeasured 0",
                "  awawa-task",
                "    runs p50 30  p90 90  measured 5  partial 0  unmeasured 1",
                "    segments p50 30  p90 90  measured 5  unmeasured 1",
            ],
        )


class BrigadeLedgerBudgetsWithNoMeasuredRunTest(LedgerTestCase):
    def test_should_print_no_percentile_for_a_procedure_whose_runs_report_no_steps(self):
        # Arrange
        self.write_ledger("2026-10", UNMEASURED_RUN_LINES)

        # Act
        completed = self.run_ledger("budgets")

        # Assert
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "steps over the last 20 runs finished of each procedure:",
                "  awawa-study  estimate",
                "    runs p50 -  p90 -  measured 0  partial 0  unmeasured 1",
                "    segments p50 -  p90 -  measured 0  unmeasured 1",
            ],
        )

    def test_should_print_the_heading_alone_with_no_ledger(self):
        # Act
        completed = self.run_ledger("budgets")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.splitlines(), ["steps over the last 20 runs finished of each procedure:"])


class BrigadeLedgerCompareTest(LedgerTestCase):
    def setUp(self):
        super().setUp()
        self.write_ledger("2026-10", COMPARISON_LINES)

    def test_should_set_the_runs_before_the_day_against_the_runs_from_that_day_on(self):
        # Act
        completed = self.run_ledger("compare", "--before", "2026-10-03", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "before": "2026-10-03",
                "periods": {
                    "before": {
                        "runs": 3,
                        "segments": 3,
                        "steps": {
                            "runs": {"measured": 2, "partial": 0, "unmeasured": 1, "p50": 40, "p90": 60},
                            "segments": {"measured": 2, "unmeasured": 1, "p50": 40, "p90": 60},
                        },
                        "steps_to_first_edit": {
                            "runs": {"measured": 1, "partial": 0, "unmeasured": 2, "p50": 12, "p90": 12},
                            "segments": {"measured": 1, "unmeasured": 2, "p50": 12, "p90": 12},
                        },
                        "oversized_output_steps": None,
                    },
                    "from": {
                        "runs": 2,
                        "segments": 2,
                        "steps": {
                            "runs": {"measured": 2, "partial": 0, "unmeasured": 0, "p50": 20, "p90": 30},
                            "segments": {"measured": 2, "unmeasured": 0, "p50": 20, "p90": 30},
                        },
                        "steps_to_first_edit": {
                            "runs": {"measured": 1, "partial": 0, "unmeasured": 1, "p50": 4, "p90": 4},
                            "segments": {"measured": 1, "unmeasured": 1, "p50": 4, "p90": 4},
                        },
                        "oversized_output_steps": {
                            "runs": {"measured": 1, "partial": 0, "unmeasured": 1, "p50": 1, "p90": 1},
                            "segments": {"measured": 1, "unmeasured": 1, "p50": 1, "p90": 1},
                        },
                    },
                },
                "skipped": [],
            },
        )

    def test_should_print_the_comparison_as_text(self):
        # Act
        completed = self.run_ledger("compare", "--before", "2026-10-03")

        # Assert
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "before 2026-10-03: 3 runs finished, 3 segments",
                "  steps:",
                "    runs p50 40  p90 60  measured 2  partial 0  unmeasured 1",
                "    segments p50 40  p90 60  measured 2  unmeasured 1",
                "  steps to first edit:",
                "    runs p50 12  p90 12  measured 1  partial 0  unmeasured 2",
                "    segments p50 12  p90 12  measured 1  unmeasured 2",
                "  oversized output steps: not reported",
                "from 2026-10-03: 2 runs finished, 2 segments",
                "  steps:",
                "    runs p50 20  p90 30  measured 2  partial 0  unmeasured 0",
                "    segments p50 20  p90 30  measured 2  unmeasured 0",
                "  steps to first edit:",
                "    runs p50 4  p90 4  measured 1  partial 0  unmeasured 1",
                "    segments p50 4  p90 4  measured 1  unmeasured 1",
                "  oversized output steps:",
                "    runs p50 1  p90 1  measured 1  partial 0  unmeasured 1",
                "    segments p50 1  p90 1  measured 1  unmeasured 1",
            ],
        )

    def test_should_exit_1_naming_the_empty_period(self):
        # Arrange
        rows = [
            ("2026-09-01", "brigade ledger compare: no run finished before 2026-09-01\n"),
            ("2026-11-01", "brigade ledger compare: no run finished from 2026-11-01 on\n"),
        ]
        for before, expected_message in rows:
            with self.subTest(before=before):
                # Act
                completed = self.run_ledger("compare", "--before", before, "--json")

                # Assert
                self.assertEqual(completed.returncode, 1)
                self.assertEqual(completed.stdout, "")
                self.assertEqual(completed.stderr, expected_message)


class BrigadeLedgerRunOfTwoSegmentsTest(LedgerTestCase):
    def setUp(self):
        super().setUp()
        self.write_ledger("2026-10", RUN_OF_TWO_SEGMENTS_LINES)

    def test_should_count_the_run_once_by_its_last_segment_beside_its_two_segments(self):
        # Act
        completed = self.run_ledger("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        document = json.loads(completed.stdout)
        self.assertEqual(document["runs"], {"outcomes": {"done": 2}, "error_classes": {}})
        self.assertEqual(document["segments"], {"outcomes": {"done": 2, "wall_limit": 1}, "error_classes": {}})

    def test_should_print_the_runs_and_the_segments_finished_as_text(self):
        # Act
        completed = self.run_ledger()

        # Assert
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "events: 3, from 2026-10-02T09:00:00Z to 2026-10-03T09:00:00Z",
                "files read: 1",
                "lines skipped: 0",
                "  run.finished  3",
                "runs finished: 2, done 2",
                "segments finished: 3, done 2, wall_limit 1",
            ],
        )

    def test_should_measure_the_budget_of_the_run_by_the_sum_of_its_measured_segments(self):
        # Arrange
        rows = [
            (
                "20",
                {
                    "runs": {"measured": 2, "partial": 1, "unmeasured": 0, "p50": 20, "p90": 30},
                    "segments": {"measured": 2, "unmeasured": 1, "p50": 20, "p90": 30},
                    "estimate": True,
                },
            ),
            (
                "1",
                {
                    "runs": {"measured": 1, "partial": 1, "unmeasured": 0, "p50": 30, "p90": 30},
                    "segments": {"measured": 1, "unmeasured": 1, "p50": 30, "p90": 30},
                    "estimate": True,
                },
            ),
        ]
        for last, expected_summary in rows:
            with self.subTest(last=last):
                # Act
                completed = self.run_ledger("budgets", "--last", last, "--json")

                # Assert
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(json.loads(completed.stdout)["procedures"], {"awawa-task": expected_summary})

    def test_should_print_the_budget_of_the_runs_and_of_the_segments_as_text(self):
        # Act
        completed = self.run_ledger("budgets")

        # Assert
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "steps over the last 20 runs finished of each procedure:",
                "  awawa-task  estimate",
                "    runs p50 20  p90 30  measured 2  partial 1  unmeasured 0",
                "    segments p50 20  p90 30  measured 2  unmeasured 1",
            ],
        )

    def test_should_date_the_run_by_its_last_segment_in_the_comparison(self):
        # Act
        completed = self.run_ledger("compare", "--before", "2026-10-03", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["periods"]["from"],
            {
                "runs": 1,
                "segments": 2,
                "steps": {
                    "runs": {"measured": 1, "partial": 1, "unmeasured": 0, "p50": 30, "p90": 30},
                    "segments": {"measured": 1, "unmeasured": 1, "p50": 30, "p90": 30},
                },
                "steps_to_first_edit": {
                    "runs": {"measured": 1, "partial": 1, "unmeasured": 0, "p50": 4, "p90": 4},
                    "segments": {"measured": 1, "unmeasured": 1, "p50": 4, "p90": 4},
                },
                "oversized_output_steps": {
                    "runs": {"measured": 1, "partial": 1, "unmeasured": 0, "p50": 1, "p90": 1},
                    "segments": {"measured": 1, "unmeasured": 1, "p50": 1, "p90": 1},
                },
            },
        )

    def test_should_print_the_comparison_of_the_runs_and_of_the_segments_as_text(self):
        # Act
        completed = self.run_ledger("compare", "--before", "2026-10-03")

        # Assert
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "before 2026-10-03: 1 runs finished, 1 segments",
                "  steps:",
                "    runs p50 20  p90 20  measured 1  partial 0  unmeasured 0",
                "    segments p50 20  p90 20  measured 1  unmeasured 0",
                "  steps to first edit:",
                "    runs p50 6  p90 6  measured 1  partial 0  unmeasured 0",
                "    segments p50 6  p90 6  measured 1  unmeasured 0",
                "  oversized output steps: not reported",
                "from 2026-10-03: 1 runs finished, 2 segments",
                "  steps:",
                "    runs p50 30  p90 30  measured 1  partial 1  unmeasured 0",
                "    segments p50 30  p90 30  measured 1  unmeasured 1",
                "  steps to first edit:",
                "    runs p50 4  p90 4  measured 1  partial 1  unmeasured 0",
                "    segments p50 4  p90 4  measured 1  unmeasured 1",
                "  oversized output steps:",
                "    runs p50 1  p90 1  measured 1  partial 1  unmeasured 0",
                "    segments p50 1  p90 1  measured 1  unmeasured 1",
            ],
        )

    def test_should_summarize_the_steps_of_the_wave_by_run_and_by_segment(self):
        # Act
        completed = self.run_ledger("--wave", "tidepool_w20", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        document = json.loads(completed.stdout)
        self.assertEqual(
            document["steps"],
            {
                "by_slot": {
                    "build": {
                        "runs": {"measured": 2, "partial": 1, "unmeasured": 0, "p50": 20, "p90": 30},
                        "segments": {"measured": 2, "unmeasured": 1, "p50": 20, "p90": 30},
                    }
                },
                "by_role": {
                    "builder": {
                        "runs": {"measured": 2, "partial": 1, "unmeasured": 0, "p50": 20, "p90": 30},
                        "segments": {"measured": 2, "unmeasured": 1, "p50": 20, "p90": 30},
                    }
                },
            },
        )

    def test_should_keep_one_hand_over_per_segment_of_the_wave(self):
        # Act
        completed = self.run_ledger("--wave", "tidepool_w20", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        document = json.loads(completed.stdout)
        self.assertEqual(document["hand_overs"], [{"task": "TP160", "role": "builder", "slot": "build", "segment": 2}])

    def test_should_print_the_steps_of_the_wave_by_run_and_by_segment_as_text(self):
        # Act
        completed = self.run_ledger("--wave", "tidepool_w20")

        # Assert
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "wave tidepool_w20: 2026-10-02T09:00:00Z to 2026-10-03T09:00:00Z, wall time 24h00m",
                "tasks: TP160, TP161",
                "pull requests: none",
                "steps by slot:",
                "  build",
                "    runs p50 20  p90 30  measured 2  partial 1  unmeasured 0",
                "    segments p50 20  p90 30  measured 2  unmeasured 1",
                "steps by role:",
                "  builder",
                "    runs p50 20  p90 30  measured 2  partial 1  unmeasured 0",
                "    segments p50 20  p90 30  measured 2  unmeasured 1",
                "pauses: 0, 0h00m in all",
                "hand-overs: TP160 builder build segment 2",
                "parked: none",
            ],
        )


class BrigadeLedgerUsageTest(LedgerTestCase):
    def test_should_refuse_an_option_out_of_its_place_with_exit_2(self):
        # Arrange
        rows = [
            (("--since", "7d"), "--since needs --project"),
            (("--wave", "tidepool_w16", "--project", "tidepool"), "not allowed with argument"),
            (
                ("--project", "tidepool", "--since", "yesterday"),
                "brigade ledger: error: argument --since: 'yesterday' is neither <n>d nor a day YYYY-MM-DD\n",
            ),
            (("budgets", "--last", "0"), "argument --last"),
            (("compare",), "the following arguments are required: --before"),
            (("compare", "--before", "2026-13-01"), "argument --before"),
        ]
        for arguments, expected_message in rows:
            with self.subTest(arguments=arguments):
                # Act
                completed = self.run_ledger(*arguments)

                # Assert
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(completed.stdout, "")
                self.assertIn(expected_message, completed.stderr)
