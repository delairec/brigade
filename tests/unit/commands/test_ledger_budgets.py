import argparse
import tempfile
import unittest
from pathlib import Path

from brigade.commands.ledger_budgets import COMMAND, ledger_budgets
from tests.unit.commands.create_command_runtime import create_command_runtime

RUN_FINISHED = (
    '{"schema_version": 2, "ts": "2026-10-09T10:33:00Z", "event": "run.finished", "run": "20261009T101817Z-2ee96f",'
    ' "segment": 1, "procedure": "awawa-task", "slot": "build", "role": "ada", "client": "claude-code",'
    ' "project": "brigade", "session": "857d4221", "main_steps": 42, "total_steps": 54, "duration_ms": 900000,'
    ' "usage": null, "outcome": "done", "error_class": null, "exit": 0, "wave": null, "task": null,'
    ' "nulls": {"usage": "the client reported no usage"}, "cost_usd": 3.63}\n'
)


class LedgerBudgetsTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.runtime = create_command_runtime(Path(self.root.name))
        self.ledger_file = self.runtime.paths.state_root / "ledger" / "2026-10.jsonl"
        self.ledger_file.parent.mkdir(parents=True)
        self.ledger_file.write_text(RUN_FINISHED + "not a document\n")

    def test_should_give_the_steps_of_each_procedure_and_the_lines_skipped(self):
        # Arrange
        request = argparse.Namespace(last=20)

        # Act
        document = ledger_budgets(request, self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "last": 20,
                "procedures": {
                    "awawa-task": {
                        "runs": {"p50": 42, "p90": 42, "measured": 1, "partial": 0, "unmeasured": 0},
                        "segments": {"p50": 42, "p90": 42, "measured": 1, "unmeasured": 0},
                        "estimate": True,
                    }
                },
                "skipped": [{"file": str(self.ledger_file), "line": 2, "reason": "not JSON"}],
            },
        )


class LedgerBudgetsRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_they_are(self):
        # Arrange
        options = argparse.Namespace(last=5)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertEqual(request, argparse.Namespace(last=5))


class LedgerBudgetsExitCodeTest(unittest.TestCase):
    def test_should_exit_0_once_the_journal_is_read(self):
        # Arrange
        document = {"last": 20, "procedures": {}}

        # Act
        exit_code = COMMAND.decide_exit_code(document)

        # Assert
        self.assertEqual(exit_code, 0)


class LedgerBudgetsTextTest(unittest.TestCase):
    def test_should_mark_the_procedures_whose_budget_is_an_estimate(self):
        # Arrange
        task_steps = {
            "runs": {"p50": 40, "p90": 52, "measured": 2, "partial": 0, "unmeasured": 0},
            "segments": {"p50": 40, "p90": 52, "measured": 2, "unmeasured": 0},
            "estimate": True,
        }
        review_steps = {
            "runs": {"p50": 20, "p90": 31, "measured": 12, "partial": 1, "unmeasured": 0},
            "segments": {"p50": None, "p90": None, "measured": 0, "unmeasured": 13},
            "estimate": False,
        }
        document = {"last": 20, "procedures": {"awawa-task": task_steps, "awawa-review": review_steps}}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "steps over the last 20 runs finished of each procedure:\n"
            "  awawa-task  estimate\n"
            "    runs p50 40  p90 52  measured 2  partial 0  unmeasured 0\n"
            "    segments p50 40  p90 52  measured 2  unmeasured 0\n"
            "  awawa-review\n"
            "    runs p50 20  p90 31  measured 12  partial 1  unmeasured 0\n"
            "    segments p50 -  p90 -  measured 0  unmeasured 13",
        )
