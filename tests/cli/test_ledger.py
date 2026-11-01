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


class BrigadeLedgerOverviewTest(LedgerTestCase):
    def setUp(self):
        super().setUp()
        self.september = self.write_ledger("2026-09", WAVE_SEPTEMBER_LINES)
        self.october = self.write_ledger("2026-10", WAVE_OCTOBER_LINES)

    def test_should_print_the_overview_as_text_and_report_the_skipped_line_on_stderr(self):
        # Act
        completed = self.run_ledger()

        # Assert
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stderr, f"brigade ledger: skipped {self.october}:3: not JSON\n")
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


class BrigadeLedgerWaveTest(LedgerTestCase):
    def setUp(self):
        super().setUp()
        self.write_ledger("2026-09", WAVE_SEPTEMBER_LINES)
        self.october = self.write_ledger("2026-10", WAVE_OCTOBER_LINES)

    def test_should_print_the_wave_as_text(self):
        # Act
        completed = self.run_ledger("--wave", "tidepool_w16")

        # Assert
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stderr, f"brigade ledger: skipped {self.october}:3: not JSON\n")
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "wave tidepool_w16: 2026-09-30T22:00:00Z to 2026-10-01T01:40:00Z, wall time 3h40m",
                "cost: none",
                "tokens: none",
                "tasks:",
                "  TP146  steps 92  duration 0h00m  cost -",
                "  TP147  steps -  duration 0h00m  cost -",
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


class BrigadeLedgerProjectTest(LedgerTestCase):
    def setUp(self):
        super().setUp()
        self.write_ledger("2026-09", PROJECT_SEPTEMBER_LINES)
        self.write_ledger("2026-10", PROJECT_OCTOBER_LINES)

    def test_should_print_the_counts_as_text(self):
        # Act
        completed = self.run_ledger("--project", "tidepool", "--since", "2026-10-01")

        # Assert
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stderr, "")
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


class BrigadeLedgerBudgetsTest(LedgerTestCase):
    def setUp(self):
        super().setUp()
        self.write_ledger("2026-10", BUDGET_LINES)

    def test_should_print_the_budgets_as_text(self):
        # Act
        completed = self.run_ledger("budgets")

        # Assert
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stderr, "")
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


class BrigadeLedgerCompareTest(LedgerTestCase):
    def setUp(self):
        super().setUp()
        self.write_ledger("2026-10", COMPARISON_LINES)

    def test_should_print_the_comparison_as_text(self):
        # Act
        completed = self.run_ledger("compare", "--range", "2026-10-01..2026-10-02", "--range", "2026-10-03..2026-10-04")

        # Assert
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stderr, "")
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "from 2026-10-01 to 2026-10-02: 3 runs finished, 3 segments",
                "  steps:",
                "    runs p50 40  p90 60  measured 2  partial 0  unmeasured 1",
                "    segments p50 40  p90 60  measured 2  unmeasured 1",
                "  steps to first edit:",
                "    runs p50 12  p90 12  measured 1  partial 0  unmeasured 2",
                "    segments p50 12  p90 12  measured 1  unmeasured 2",
                "  oversized output steps: not reported",
                "  steps to first edit p50: 12",
                "  steps per task run p50: 40",
                "  oversized output steps per launch: -",
                "from 2026-10-03 to 2026-10-04: 2 runs finished, 2 segments",
                "  steps:",
                "    runs p50 20  p90 30  measured 2  partial 0  unmeasured 0",
                "    segments p50 20  p90 30  measured 2  unmeasured 0",
                "  steps to first edit:",
                "    runs p50 4  p90 4  measured 1  partial 0  unmeasured 1",
                "    segments p50 4  p90 4  measured 1  unmeasured 1",
                "  oversized output steps:",
                "    runs p50 1  p90 1  measured 1  partial 0  unmeasured 1",
                "    segments p50 1  p90 1  measured 1  unmeasured 1",
                "  steps to first edit p50: 4",
                "  steps per task run p50: 20",
                "  oversized output steps per launch: 1",
            ],
        )

    def test_should_print_the_reference_figures_after_the_range(self):
        # Act
        completed = self.run_ledger(
            "compare", "--range", "2026-10-03..2026-10-04", "--reference", "task_run_steps_p50=47"
        )

        # Assert
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout.splitlines()[-2:], ["reference:", "  steps per task run p50: 47"])
