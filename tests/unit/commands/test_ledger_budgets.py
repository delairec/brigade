import argparse
import tempfile
import unittest
from pathlib import Path

from brigade.commands.ledger_budgets import COMMAND, ledger_budgets

RUN_FINISHED = (
    '{"schema_version": 2, "ts": "2026-10-09T10:33:00Z", "event": "run.finished", "run": "20261009T101817Z-2ee96f",'
    ' "segment": 1, "procedure": "awawa-task", "slot": "build", "role": "ada", "client": "claude-code",'
    ' "project": "brigade", "session": "857d4221", "main_steps": 42, "total_steps": 54, "duration_ms": 900000,'
    ' "usage": null, "outcome": "done", "error_class": null, "exit": 0, "wave": null, "task": null,'
    ' "nulls": {"usage": "the client reported no usage"}, "cost_usd": 3.63, "shipped_budget": 75}\n'
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime


class LedgerBudgetsTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.runtime = create_test_runtime(create_test_paths(Path(self.root.name)))
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
                "roles": {
                    "ada": {
                        "shipped": 75,
                        "computed": None,
                        "applied": 75,
                        "segments": 0,
                        "restarts": 0,
                        "growth": None,
                        "restart_tokens": None,
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
    def test_should_print_the_headings_alone_when_no_run_finished(self):
        # Arrange
        no_procedures = {}
        no_roles = {}
        document = {"last": 20, "procedures": no_procedures, "roles": no_roles}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "steps over the last 20 runs finished of each procedure:\nstep cap of each role at its latest digests:",
        )

    def test_should_print_the_step_cap_of_each_role_and_the_measures_it_rests_on(self):
        # Arrange
        no_procedures = {}
        ada = {
            "shipped": 75,
            "computed": 132,
            "applied": 132,
            "segments": 6,
            "restarts": 3,
            "growth": 2500.4,
            "restart_tokens": 21666.6,
        }
        remi = {
            "shipped": 50,
            "computed": None,
            "applied": 50,
            "segments": 2,
            "restarts": 0,
            "growth": None,
            "restart_tokens": None,
        }
        document = {"last": 20, "procedures": no_procedures, "roles": {"ada": ada, "remi": remi}}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "steps over the last 20 runs finished of each procedure:\n"
            "step cap of each role at its latest digests:\n"
            "  ada  shipped 75  computed 132  applied 132  segments 6  restarts 3  g 2500  R 21667\n"
            "  remi  shipped 50  computed -  applied 50  segments 2  restarts 0  g -  R -",
        )

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
        no_roles = {}
        document = {
            "last": 20,
            "procedures": {"awawa-task": task_steps, "awawa-review": review_steps},
            "roles": no_roles,
        }

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
            "    segments p50 -  p90 -  measured 0  unmeasured 13\n"
            "step cap of each role at its latest digests:",
        )
