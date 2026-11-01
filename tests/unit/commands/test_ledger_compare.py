import argparse
import tempfile
import unittest
from datetime import date
from pathlib import Path

from brigade.commands.ledger_compare import COMMAND, ledger_compare
from brigade.errors import UsageError
from brigade.system.read_day_range import DayRange

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
SEPTEMBER = DayRange(start=date(2026, 9, 1), end=date(2026, 9, 30))
OCTOBER = DayRange(start=date(2026, 10, 1), end=date(2026, 10, 31))
NOVEMBER = DayRange(start=date(2026, 11, 1), end=date(2026, 11, 30))
STEPS = {
    "runs": {"p50": 40, "p90": 52, "measured": 2, "partial": 0, "unmeasured": 0},
    "segments": {"p50": 40, "p90": 52, "measured": 2, "unmeasured": 0},
}
SEPTEMBER_RANGE = {
    "start": "2026-09-01",
    "end": "2026-09-30",
    "runs": 2,
    "segments": 2,
    "steps": STEPS,
    "steps_to_first_edit": None,
    "oversized_output_steps": None,
    "figures": {"steps_to_first_edit_p50": None, "task_run_steps_p50": 40, "oversized_output_steps_per_launch": None},
}
OCTOBER_RANGE = {
    "start": "2026-10-01",
    "end": "2026-10-31",
    "runs": 2,
    "segments": 3,
    "steps": STEPS,
    "steps_to_first_edit": STEPS,
    "oversized_output_steps": STEPS,
    "figures": {"steps_to_first_edit_p50": 40, "task_run_steps_p50": 40, "oversized_output_steps_per_launch": 1.5},
}
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

    def test_should_set_one_range_of_days_against_the_other(self):
        # Arrange
        request = argparse.Namespace(ranges=(SEPTEMBER, OCTOBER), reference={})

        # Act
        document = ledger_compare(request, self.runtime)

        # Assert
        self.assertEqual(document["skipped"], [{"file": str(self.october), "line": 2, "reason": "not JSON"}])


class LedgerCompareRequestTest(unittest.TestCase):
    def test_should_take_two_ranges_or_one_range_and_reference_figures(self):
        for ranges, references, expected in [
            ([SEPTEMBER, OCTOBER], None, argparse.Namespace(ranges=(SEPTEMBER, OCTOBER), reference={})),
            (
                [OCTOBER],
                [("task_run_steps_p50", 47.0), ("steps_to_first_edit_p50", 23.0)],
                argparse.Namespace(
                    ranges=(OCTOBER,), reference={"task_run_steps_p50": 47.0, "steps_to_first_edit_p50": 23.0}
                ),
            ),
        ]:
            with self.subTest(ranges=ranges, references=references):
                # Arrange
                options = argparse.Namespace(range=ranges, reference=references)

                # Act
                request = COMMAND.read_request(options)

                # Assert
                self.assertEqual(request, expected)

    def test_should_refuse_a_comparison_without_two_sides(self):
        for ranges, references in [
            ([OCTOBER], None),
            ([SEPTEMBER, OCTOBER], [("task_run_steps_p50", 47.0)]),
            ([SEPTEMBER, OCTOBER, NOVEMBER], None),
        ]:
            with self.subTest(ranges=ranges, references=references):
                # Arrange
                options = argparse.Namespace(range=ranges, reference=references)

                # Act
                with self.assertRaises(UsageError) as refusal:
                    COMMAND.read_request(options)

                # Assert
                self.assertEqual(str(refusal.exception), "compare takes two --range, or one --range and --reference")


class LedgerCompareExitCodeTest(unittest.TestCase):
    def test_should_exit_0_once_the_journal_is_read(self):
        # Arrange
        document = {"ranges": [], "reference": {}}

        # Act
        exit_code = COMMAND.decide_exit_code(document)

        # Assert
        self.assertEqual(exit_code, 0)


class LedgerCompareTextTest(unittest.TestCase):
    def test_should_present_each_range_and_the_measures_it_reports(self):
        # Arrange
        document = {"ranges": [SEPTEMBER_RANGE, OCTOBER_RANGE], "reference": {}}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "from 2026-09-01 to 2026-09-30: 2 runs finished, 2 segments\n"
            "  steps:\n"
            "    runs p50 40  p90 52  measured 2  partial 0  unmeasured 0\n"
            "    segments p50 40  p90 52  measured 2  unmeasured 0\n"
            "  steps to first edit: not reported\n"
            "  oversized output steps: not reported\n"
            "  steps to first edit p50: -\n"
            "  steps per task run p50: 40\n"
            "  oversized output steps per launch: -\n"
            "from 2026-10-01 to 2026-10-31: 2 runs finished, 3 segments\n"
            "  steps:\n"
            "    runs p50 40  p90 52  measured 2  partial 0  unmeasured 0\n"
            "    segments p50 40  p90 52  measured 2  unmeasured 0\n"
            "  steps to first edit:\n"
            "    runs p50 40  p90 52  measured 2  partial 0  unmeasured 0\n"
            "    segments p50 40  p90 52  measured 2  unmeasured 0\n"
            "  oversized output steps:\n"
            "    runs p50 40  p90 52  measured 2  partial 0  unmeasured 0\n"
            "    segments p50 40  p90 52  measured 2  unmeasured 0\n"
            "  steps to first edit p50: 40\n"
            "  steps per task run p50: 40\n"
            "  oversized output steps per launch: 1.5",
        )

    def test_should_present_the_reference_figures_after_the_range(self):
        # Arrange
        document = {
            "ranges": [SEPTEMBER_RANGE],
            "reference": {"steps_to_first_edit_p50": 23.0, "oversized_output_steps_per_launch": 2.18},
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text.splitlines()[-3:],
            ["reference:", "  steps to first edit p50: 23", "  oversized output steps per launch: 2.18"],
        )
