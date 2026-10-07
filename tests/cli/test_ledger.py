import json
import tempfile
import unittest
from pathlib import Path

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine

WAVE_SEPTEMBER_LINES = (
    '{"schema_version": 1, "ts": "2026-09-30T22:00:00Z", "event": "wave.started", "wave": "tp/16",'
    ' "project": "tidepool"}\n'
    '{"schema_version": 1, "ts": "2026-09-30T22:10:00Z", "event": "run.finished", "wave": "tp/16", "task": "TP146",'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "failed",'
    ' "error_class": "rate_limit", "steps": 50}\n'
    '{"schema_version": 1, "ts": "2026-09-30T22:15:00Z", "event": "wave.paused", "wave": "tp/16"}\n'
)
WAVE_OCTOBER_LINES = (
    '{"schema_version": 1, "ts": "2026-10-01T00:15:00Z", "event": "wave.resumed", "wave": "tp/16"}\n'
    '{"schema_version": 1, "ts": "2026-10-01T00:40:00Z", "event": "run.finished", "wave": "tp/16", "task": "TP146",'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 2, "outcome": "done",'
    ' "error_class": null, "steps": 30}\n'
    '{"schema_version": 1, "ts": "2026-10-01T00:41\n'
    '{"schema_version": 1, "ts": "2026-10-01T00:50:00Z", "event": "run.finished", "wave": "tp/16", "task": "TP147",'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "steps": null}\n'
    '{"schema_version": 1, "ts": "2026-10-01T01:00:00Z", "event": "run.finished", "wave": "tp/16", "task": "TP146",'
    ' "procedure": "awawa-pr-review", "role": "remi", "slot": "review", "segment": 1, "outcome": "done",'
    ' "error_class": null, "steps": 12}\n'
    '{"schema_version": 1, "ts": "2026-10-01T01:30:00Z", "event": "pr.merged", "project": "tidepool", "wave": "tp/16",'
    ' "task": "TP146", "pr": 291, "rounds": 1}\n'
    '{"schema_version": 1, "ts": "2026-10-01T01:40:00Z", "event": "task.parked", "wave": "tp/16", "task": "TP147"}\n'
    '{"schema_version": 1, "ts": "2026-10-01T02:00:00Z", "event": "run.finished", "wave": "tp/17", "task": "TP150",'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "steps": 20}\n'
)
BUDGET_LINES = (
    '{"schema_version": 1, "ts": "2026-10-01T08:00:00Z", "event": "run.finished", "wave": "tp/16", "task": "TP146",'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "steps": 90}\n'
    '{"schema_version": 1, "ts": "2026-10-01T09:00:00Z", "event": "run.finished", "wave": "tp/16", "task": "TP147",'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "steps": 80}\n'
    '{"schema_version": 1, "ts": "2026-10-01T10:00:00Z", "event": "run.finished", "wave": "tp/16", "task": "TP146",'
    ' "procedure": "awawa-pr-review", "role": "remi", "slot": "review", "segment": 1, "outcome": "done",'
    ' "error_class": null, "steps": 12}\n'
    '{"schema_version": 1, "ts": "2026-10-01T11:00:00Z", "event": "run.finished", "wave": "tp/16", "task": "TP148",'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "steps": null}\n'
    '{"schema_version": 1, "ts": "2026-10-01T12:00:00Z", "event": "run.finished", "wave": "tp/16", "task": "TP149",'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "steps": 10}\n'
    '{"schema_version": 1, "ts": "2026-10-01T13:00:00Z", "event": "run.finished", "wave": "tp/16", "task": "TP147",'
    ' "procedure": "awawa-pr-review", "role": "remi", "slot": "review", "segment": 1, "outcome": "done",'
    ' "error_class": null, "steps": 8}\n'
    '{"schema_version": 1, "ts": "2026-10-01T14:00:00Z", "event": "run.finished", "wave": "tp/16", "task": "TP150",'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "steps": 20}\n'
    '{"schema_version": 1, "ts": "2026-10-01T15:00:00Z", "event": "run.finished", "wave": "tp/16", "task": "TP151",'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "steps": 30}\n'
)
COMPARISON_LINES = (
    '{"schema_version": 1, "ts": "2026-10-01T08:00:00Z", "event": "wave.started", "wave": "tp/16",'
    ' "project": "tidepool"}\n'
    '{"schema_version": 1, "ts": "2026-10-01T09:00:00Z", "event": "run.finished", "wave": "tp/16", "task": "TP146",'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "steps": 40, "steps_to_first_edit": 12}\n'
    '{"schema_version": 1, "ts": "2026-10-02T09:00:00Z", "event": "run.finished", "wave": "tp/16", "task": "TP147",'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "steps": 60}\n'
    '{"schema_version": 1, "ts": "2026-10-02T23:59:59Z", "event": "run.finished", "wave": "tp/16", "task": "TP148",'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "steps": null}\n'
    '{"schema_version": 1, "ts": "2026-10-03T00:00:00Z", "event": "run.finished", "wave": "tp/17", "task": "TP150",'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "steps": 20, "steps_to_first_edit": 4, "oversized_output_steps": 1}\n'
    '{"schema_version": 1, "ts": "2026-10-04T09:00:00Z", "event": "run.finished", "wave": "tp/17", "task": "TP151",'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "steps": 30}\n'
)
PROJECT_SEPTEMBER_LINES = (
    '{"schema_version": 1, "ts": "2026-09-20T08:00:00Z", "event": "wave.started", "wave": "tp/15",'
    ' "project": "tidepool"}\n'
)
PROJECT_OCTOBER_LINES = (
    '{"schema_version": 1, "ts": "2026-10-02T08:00:00Z", "event": "wave.started", "wave": "tp/16",'
    ' "project": "tidepool"}\n'
    '{"schema_version": 1, "ts": "2026-10-02T08:00:00Z", "event": "wave.started", "wave": "ob/3",'
    ' "project": "oboe"}\n'
    '{"schema_version": 1, "ts": "2026-10-02T09:00:00Z", "event": "order.done", "project": "tidepool",'
    ' "kind": "study"}\n'
    '{"schema_version": 1, "ts": "2026-10-02T10:00:00Z", "event": "order.done", "project": "tidepool",'
    ' "kind": "intake"}\n'
    '{"schema_version": 1, "ts": "2026-10-02T11:00:00Z", "event": "order.done", "project": "tidepool",'
    ' "kind": "study"}\n'
    '{"schema_version": 1, "ts": "2026-10-02T11:00:00Z", "event": "order.done", "project": "oboe", "kind": "study"}\n'
    '{"schema_version": 1, "ts": "2026-10-02T12:00:00Z", "event": "pr.merged", "project": "tidepool", "wave": "tp/16",'
    ' "task": "TP146", "pr": 291, "rounds": 1}\n'
    '{"schema_version": 1, "ts": "2026-10-02T13:00:00Z", "event": "signal.recorded", "project": "tidepool"}\n'
    '{"schema_version": 1, "ts": "2026-10-02T14:00:00Z", "event": "pattern.ratified", "project": "tidepool"}\n'
    '{"schema_version": 1, "ts": "2026-10-02T15:00:00Z", "event": "constraint.delivered", "project": "tidepool"}\n'
)
OLD_WAVE_LINES = (
    '{"schema_version": 1, "ts": "2020-01-01T08:00:00Z", "event": "wave.started", "wave": "tp/1",'
    ' "project": "tidepool"}\n'
)
REPEATED_PAUSE_LINES = (
    '{"schema_version": 1, "ts": "2026-10-01T08:00:00Z", "event": "wave.started", "wave": "tp/18",'
    ' "project": "tidepool"}\n'
    '{"schema_version": 1, "ts": "2026-10-01T09:00:00Z", "event": "wave.paused", "wave": "tp/18"}\n'
    '{"schema_version": 1, "ts": "2026-10-01T09:30:00Z", "event": "wave.paused", "wave": "tp/18"}\n'
    '{"schema_version": 1, "ts": "2026-10-01T10:00:00Z", "event": "wave.resumed", "wave": "tp/18"}\n'
    '{"schema_version": 1, "ts": "2026-10-01T10:30:00Z", "event": "wave.resumed", "wave": "tp/18"}\n'
)
UNMEASURED_RUN_LINES = (
    '{"schema_version": 1, "ts": "2026-10-01T08:00:00Z", "event": "run.finished", "wave": "tp/16", "task": "TP146",'
    ' "procedure": "awawa-study", "role": "dora", "slot": "study", "segment": 1, "outcome": "done",'
    ' "error_class": null, "steps": null}\n'
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
                "runs": {"outcomes": {"done": 4, "failed": 1}, "error_classes": {"rate_limit": 1}},
            },
        )

    def test_should_report_the_skipped_line_on_stderr_and_still_exit_0(self):
        # Act
        completed = self.run_ledger()

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr),
            (0, f"brigade ledger: skipped {self.october}:3: not JSON\n"),
        )

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
                "runs finished: done 4, failed 1",
                "error classes: rate_limit 1",
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
            },
        )

    def test_should_print_zero_events_as_text(self):
        # Act
        completed = self.run_ledger()

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout.splitlines()),
            (0, ["events: 0", "files read: 0", "lines skipped: 0"]),
        )


class BrigadeLedgerWaveTest(LedgerTestCase):
    def setUp(self):
        super().setUp()
        self.write_ledger("2026-09", WAVE_SEPTEMBER_LINES)
        self.october = self.write_ledger("2026-10", WAVE_OCTOBER_LINES)

    def test_should_describe_the_tasks_steps_pauses_hand_overs_and_parked_tasks_of_the_wave(self):
        # Act
        completed = self.run_ledger("--wave", "tp/16", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "view": "wave",
                "wave": "tp/16",
                "first": "2026-09-30T22:00:00Z",
                "last": "2026-10-01T01:40:00Z",
                "wall_time_ms": 13200000,
                "tasks": ["TP146", "TP147"],
                "pull_requests": [{"task": "TP146", "pr": 291, "rounds": 1}],
                "steps": {
                    "by_slot": {
                        "build": {"measured": 2, "unmeasured": 1, "p50": 30, "p90": 50},
                        "review": {"measured": 1, "unmeasured": 0, "p50": 12, "p90": 12},
                    },
                    "by_role": {
                        "builder": {"measured": 2, "unmeasured": 1, "p50": 30, "p90": 50},
                        "remi": {"measured": 1, "unmeasured": 0, "p50": 12, "p90": 12},
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
        completed = self.run_ledger("--wave", "tp/16")

        # Assert
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "wave tp/16: 2026-09-30T22:00:00Z to 2026-10-01T01:40:00Z, wall time 3h40m",
                "tasks: TP146, TP147",
                "pull requests: #291 TP146 rounds 1",
                "steps by slot:",
                "  build   p50 30  p90 50  measured 2  unmeasured 1",
                "  review  p50 12  p90 12  measured 1  unmeasured 0",
                "steps by role:",
                "  builder  p50 30  p90 50  measured 2  unmeasured 1",
                "  remi     p50 12  p90 12  measured 1  unmeasured 0",
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
        completed = self.run_ledger("--wave", "tp/16", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        document = json.loads(completed.stdout)
        self.assertEqual(
            (document["pauses"], document["paused_ms"]),
            ([{"paused_at": "2026-09-30T22:15:00Z", "resumed_at": None, "duration_ms": None}], 0),
        )

    def test_should_print_the_open_pause_as_text(self):
        # Arrange
        self.write_ledger("2026-09", WAVE_SEPTEMBER_LINES)

        # Act
        completed = self.run_ledger("--wave", "tp/16")

        # Assert
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "wave tp/16: 2026-09-30T22:00:00Z to 2026-09-30T22:15:00Z, wall time 0h15m",
                "tasks: TP146",
                "pull requests: none",
                "steps by slot:",
                "  build  p50 50  p90 50  measured 1  unmeasured 0",
                "steps by role:",
                "  builder  p50 50  p90 50  measured 1  unmeasured 0",
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
        completed = self.run_ledger("--wave", "tp/18", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        document = json.loads(completed.stdout)
        self.assertEqual(
            (document["pauses"], document["paused_ms"]),
            (
                [{"paused_at": "2026-10-01T09:00:00Z", "resumed_at": "2026-10-01T10:00:00Z", "duration_ms": 3600000}],
                3600000,
            ),
        )

    def test_should_print_none_for_what_the_wave_did_not_do(self):
        # Act
        completed = self.run_ledger("--wave", "tp/18")

        # Assert
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "wave tp/18: 2026-10-01T08:00:00Z to 2026-10-01T10:30:00Z, wall time 2h30m",
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
        completed = self.run_ledger("--wave", "tp/99", "--json")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (1, "", "brigade ledger: no event names the wave tp/99\n"),
        )


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
        self.assertEqual((document["since"], document["waves_started"]), ("2026-10-01T00:00:00Z", 1))

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
        self.assertEqual(
            (completed.returncode, completed.stdout.splitlines()),
            (
                0,
                [
                    "project tidepool",
                    "waves started: 0",
                    "orders done: 0",
                    "pull requests merged: 0",
                    "signals recorded: 0",
                    "patterns ratified: 0",
                    "constraints delivered: 0",
                ],
            ),
        )


class BrigadeLedgerProjectSinceADayCountTest(LedgerTestCase):
    def test_should_count_the_days_back_from_now(self):
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
                    "awawa-pr-review": {"measured": 2, "unmeasured": 0, "p50": 8, "p90": 12, "estimate": True},
                    "awawa-task": {"measured": 5, "unmeasured": 1, "p50": 30, "p90": 90, "estimate": False},
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
            {"measured": 3, "unmeasured": 0, "p50": 20, "p90": 30, "estimate": True},
        )

    def test_should_print_the_budgets_as_text(self):
        # Act
        completed = self.run_ledger("budgets")

        # Assert
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "steps over the last 20 runs finished of each procedure:",
                "  awawa-pr-review  p50 8  p90 12  measured 2  unmeasured 0  estimate",
                "  awawa-task       p50 30  p90 90  measured 5  unmeasured 1",
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
                "  awawa-study  p50 -  p90 -  measured 0  unmeasured 1  estimate",
            ],
        )

    def test_should_print_the_heading_alone_with_no_ledger(self):
        # Act
        completed = self.run_ledger("budgets")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout.splitlines()),
            (0, ["steps over the last 20 runs finished of each procedure:"]),
        )


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
                        "steps": {"measured": 2, "unmeasured": 1, "p50": 40, "p90": 60},
                        "steps_to_first_edit": {"measured": 1, "unmeasured": 2, "p50": 12, "p90": 12},
                        "oversized_output_steps": None,
                    },
                    "from": {
                        "runs": 2,
                        "steps": {"measured": 2, "unmeasured": 0, "p50": 20, "p90": 30},
                        "steps_to_first_edit": {"measured": 1, "unmeasured": 1, "p50": 4, "p90": 4},
                        "oversized_output_steps": {"measured": 1, "unmeasured": 1, "p50": 1, "p90": 1},
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
                "before 2026-10-03: 3 runs finished",
                "  steps                   p50 40  p90 60  measured 2  unmeasured 1",
                "  steps to first edit     p50 12  p90 12  measured 1  unmeasured 2",
                "  oversized output steps  not reported",
                "from 2026-10-03: 2 runs finished",
                "  steps                   p50 20  p90 30  measured 2  unmeasured 0",
                "  steps to first edit     p50 4  p90 4  measured 1  unmeasured 1",
                "  oversized output steps  p50 1  p90 1  measured 1  unmeasured 1",
            ],
        )

    def test_should_exit_1_naming_the_empty_period(self):
        rows = [
            ("2026-09-01", "brigade ledger compare: no run finished before 2026-09-01\n"),
            ("2026-11-01", "brigade ledger compare: no run finished from 2026-11-01 on\n"),
        ]
        for before, expected_message in rows:
            with self.subTest(before=before):
                # Act
                completed = self.run_ledger("compare", "--before", before, "--json")

                # Assert
                self.assertEqual((completed.returncode, completed.stdout, completed.stderr), (1, "", expected_message))


class BrigadeLedgerUsageTest(LedgerTestCase):
    def test_should_refuse_an_option_out_of_its_place_with_exit_2(self):
        rows = [
            (("--since", "7d"), "--since needs --project"),
            (("--wave", "tp/16", "--project", "tidepool"), "not allowed with argument"),
            (("--project", "tidepool", "--since", "yesterday"), "argument --since"),
            (("budgets", "--last", "0"), "argument --last"),
            (("compare",), "the following arguments are required: --before"),
            (("compare", "--before", "2026-13-01"), "argument --before"),
        ]
        for arguments, expected_message in rows:
            with self.subTest(arguments=arguments):
                # Act
                completed = self.run_ledger(*arguments)

                # Assert
                self.assertEqual((completed.returncode, completed.stdout), (2, ""))
                self.assertIn(expected_message, completed.stderr)
