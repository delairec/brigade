import argparse
import tempfile
import unittest
from datetime import date
from pathlib import Path

from brigade.commands.ledger_compare import COMMAND, ledger_compare

RUN_FINISHED_BEFORE = (
    '{"schema_version": 2, "ts": "2026-09-30T10:33:00Z", "event": "run.finished", "run": "20260930T101817Z-1aa96f",'
    ' "segment": 1, "procedure": "awawa-task", "slot": "build", "role": "ada", "client": "claude-code",'
    ' "project": "brigade", "session": "757d4221", "main_steps": 60, "total_steps": 70, "duration_ms": 900000,'
    ' "usage": null, "outcome": "done", "error_class": null, "exit": 0, "wave": null, "task": null,'
    ' "nulls": {"usage": "the client reported no usage"}, "cost_usd": 3.63}\n'
)
RUN_FINISHED_FROM = (
    '{"schema_version": 2, "ts": "2026-10-09T10:33:00Z", "event": "run.finished", "run": "20261009T101817Z-2ee96f",'
    ' "segment": 1, "procedure": "awawa-task", "slot": "build", "role": "ada", "client": "claude-code",'
    ' "project": "brigade", "session": "857d4221", "main_steps": 42, "total_steps": 54, "duration_ms": 900000,'
    ' "usage": null, "outcome": "done", "error_class": null, "exit": 0, "wave": null, "task": null,'
    ' "nulls": {"usage": "the client reported no usage"}, "cost_usd": 3.63}\n'
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime


class LedgerCompareTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.runtime = create_test_runtime(create_test_paths(Path(self.root.name)))
        ledger_directory = self.runtime.paths.state_root / "ledger"
        ledger_directory.mkdir(parents=True)
        (ledger_directory / "2026-09.jsonl").write_text(RUN_FINISHED_BEFORE)
        self.october = ledger_directory / "2026-10.jsonl"
        self.october.write_text(RUN_FINISHED_FROM + "not a document\n")

    def test_should_set_the_runs_before_the_day_against_the_runs_from_it(self):
        # Arrange
        request = argparse.Namespace(before=date(2026, 10, 1))

        # Act
        document = ledger_compare(request, self.runtime)

        # Assert
        self.assertEqual(document["skipped"], [{"file": str(self.october), "line": 2, "reason": "not JSON"}])


class LedgerCompareRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_they_are(self):
        # Arrange
        options = argparse.Namespace(before=date(2026, 10, 1))

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertEqual(request, argparse.Namespace(before=date(2026, 10, 1)))


class LedgerCompareExitCodeTest(unittest.TestCase):
    def test_should_exit_0_once_the_journal_is_read(self):
        # Arrange
        document = {"before": "2026-10-01", "periods": {}}

        # Act
        exit_code = COMMAND.decide_exit_code(document)

        # Assert
        self.assertEqual(exit_code, 0)


class LedgerCompareTextTest(unittest.TestCase):
    def test_should_present_each_period_and_the_measures_it_reports(self):
        # Arrange
        steps = {
            "runs": {"p50": 40, "p90": 52, "measured": 2, "partial": 0, "unmeasured": 0},
            "segments": {"p50": 40, "p90": 52, "measured": 2, "unmeasured": 0},
        }
        document = {
            "before": "2026-10-01",
            "periods": {
                "before": {
                    "runs": 2,
                    "segments": 2,
                    "steps": steps,
                    "steps_to_first_edit": None,
                    "oversized_output_steps": None,
                },
                "from": {
                    "runs": 2,
                    "segments": 2,
                    "steps": steps,
                    "steps_to_first_edit": steps,
                    "oversized_output_steps": None,
                },
            },
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "before 2026-10-01: 2 runs finished, 2 segments\n"
            "  steps:\n"
            "    runs p50 40  p90 52  measured 2  partial 0  unmeasured 0\n"
            "    segments p50 40  p90 52  measured 2  unmeasured 0\n"
            "  steps to first edit: not reported\n"
            "  oversized output steps: not reported\n"
            "from 2026-10-01: 2 runs finished, 2 segments\n"
            "  steps:\n"
            "    runs p50 40  p90 52  measured 2  partial 0  unmeasured 0\n"
            "    segments p50 40  p90 52  measured 2  unmeasured 0\n"
            "  steps to first edit:\n"
            "    runs p50 40  p90 52  measured 2  partial 0  unmeasured 0\n"
            "    segments p50 40  p90 52  measured 2  unmeasured 0\n"
            "  oversized output steps: not reported",
        )

    def test_should_present_a_period_whose_runs_count_more_segments_than_runs(self):
        # Arrange
        steps = {
            "runs": {"p50": 30, "p90": 30, "measured": 1, "partial": 1, "unmeasured": 0},
            "segments": {"p50": 30, "p90": 30, "measured": 1, "unmeasured": 1},
        }
        period = {"runs": 1, "segments": 2, "steps": steps, "steps_to_first_edit": None, "oversized_output_steps": None}
        document = {"before": "2026-10-05", "periods": {"before": period, "from": period}}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text.splitlines()[:4],
            [
                "before 2026-10-05: 1 runs finished, 2 segments",
                "  steps:",
                "    runs p50 30  p90 30  measured 1  partial 1  unmeasured 0",
                "    segments p50 30  p90 30  measured 1  unmeasured 1",
            ],
        )
