import argparse
import contextlib
import json
import tempfile
import unittest
from pathlib import Path

from brigade.commands.order_run import COMMAND, order_run
from brigade.ledger.append_event import append_event
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.order_done import OrderDone
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.order_started import OrderStarted
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.step_done import StepDone
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import FIXED_NOW, create_test_runtime
from tests.unit.recipes.checkout_answers import create_checkout_answers
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers
from tests.unit.select_argvs_run_in import select_argvs_run_in
from tests.value_matchers import PatternMatcher

PARKED_RUN = "20261018T090000Z-aaaaaa"
USAGE_REPORT = (
    'schema_version = 1\nname = "usage-report"\ndescription = "the usage report of a pull request"\n'
    'params = ["pull_request"]\nmax_wall = 30\n'
    '[[steps]]\nkind = "command"\nargv = ["make", "collect", "PR={pull_request}"]\n'
    '[[steps]]\nkind = "command"\nargv = ["make", "report", "{project}"]\n'
)
NIGHTLY = ProcessAnswer(
    stdout=json.dumps(
        {
            "fields": [
                {"name": "RECIPE", "atoms": ['"usage-report"']},
                {"name": "PROJECT", "atoms": ['"@PROJECT.shop"']},
                {"name": "PARAM", "atoms": ['"pull_request=12"']},
                {"name": "STATUS", "atoms": ['"active"']},
            ]
        }
    )
)
NEW_RUN = PatternMatcher("20261019T090000Z-[0-9a-f]{6}")


class OrderRunTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name).resolve()
        write_operational_corpus(root)
        self.paths = create_test_paths(root)
        (self.paths.config_root / "recipes").mkdir()
        (self.paths.config_root / "recipes" / "usage-report.toml").write_text(USAGE_REPORT, encoding="utf-8")
        self.shop = root / "shop"
        self.shop.mkdir()
        self.enterContext(contextlib.chdir(self.shop))
        config = str(self.paths.config_root)
        self.runner = RecordingProcessRunner(
            {
                **create_registry_answers(self.paths.config_root, {"shop": {"PATH": str(self.shop), "MODE": "none"}}),
                **create_checkout_answers(self.shop, self.shop),
                ("awawa", "show", "@ORDER.nightly", "--json", config): NIGHTLY,
            }
        )
        self.runtime = create_test_runtime(self.paths, run_process=self.runner)

    def test_should_run_the_steps_of_the_recipe_of_the_order_in_its_project(self):
        # Act
        document = order_run(argparse.Namespace(name="nightly"), self.runtime)

        # Assert
        self.assertEqual(document, {"schema_version": 1, "order": "nightly", "run": NEW_RUN, "state": "done"})
        self.assertEqual(
            select_argvs_run_in(self.runner.requests, str(self.shop)),
            [("make", "collect", "PR=12"), ("make", "report", "shop")],
        )

    def test_should_record_the_run_of_the_order_under_the_name_of_its_recipe(self):
        # Act
        order_run(argparse.Namespace(name="nightly"), self.runtime)

        # Assert
        self.assertEqual(
            read_ledger(self.paths.state_root).entries,
            (
                LedgerEntry(
                    instant=FIXED_NOW,
                    event=OrderStarted(project="shop", kind="usage-report", order="nightly", run=NEW_RUN),
                ),
                LedgerEntry(instant=FIXED_NOW, event=StepDone(kind="usage-report", run=NEW_RUN, step="1-command")),
                LedgerEntry(instant=FIXED_NOW, event=StepDone(kind="usage-report", run=NEW_RUN, step="2-command")),
                LedgerEntry(
                    instant=FIXED_NOW,
                    event=OrderDone(project="shop", kind="usage-report", order="nightly", run=NEW_RUN),
                ),
            ),
        )

    def test_should_resume_a_parked_order_at_its_first_undone_step(self):
        # Arrange
        append_event(
            self.paths, FIXED_NOW, OrderStarted(project="shop", kind="usage-report", order="nightly", run=PARKED_RUN)
        )
        append_event(self.paths, FIXED_NOW, StepDone(kind="usage-report", run=PARKED_RUN, step="1-command"))
        append_event(
            self.paths,
            FIXED_NOW,
            OrderParked(
                project="shop", kind="usage-report", order="nightly", run=PARKED_RUN, step="2-command", reason="red"
            ),
        )
        steps = self.paths.state_root / "runs" / PARKED_RUN / "steps"
        steps.mkdir(parents=True)
        (steps / "1-command.json").write_text("{}", encoding="utf-8")

        # Act
        document = order_run(argparse.Namespace(name="nightly"), self.runtime)

        # Assert
        self.assertEqual(document, {"schema_version": 1, "order": "nightly", "run": PARKED_RUN, "state": "done"})
        self.assertEqual(select_argvs_run_in(self.runner.requests, str(self.shop)), [("make", "report", "shop")])

    def test_should_start_a_new_run_when_a_study_of_the_same_name_parked(self):
        # Arrange
        append_event(self.paths, FIXED_NOW, OrderStarted(project="shop", kind="study", order="nightly", run=PARKED_RUN))
        append_event(
            self.paths,
            FIXED_NOW,
            OrderParked(project="shop", kind="study", order="nightly", run=PARKED_RUN, step="judge", reason="red"),
        )

        # Act
        document = order_run(argparse.Namespace(name="nightly"), self.runtime)

        # Assert
        self.assertEqual(document, {"schema_version": 1, "order": "nightly", "run": NEW_RUN, "state": "done"})


class OrderRunTextTest(unittest.TestCase):
    def test_should_print_the_outcome_of_the_run_and_exit_on_it(self):
        # Arrange
        rows = [
            (
                "a run done",
                {"schema_version": 1, "order": "nightly", "run": PARKED_RUN, "state": "done"},
                "@ORDER.nightly run 20261018T090000Z-aaaaaa done",
                0,
            ),
            (
                "a run parked",
                {
                    "schema_version": 1,
                    "order": "nightly",
                    "run": PARKED_RUN,
                    "state": "parked",
                    "step": "2-gate",
                    "reason": "red",
                },
                "@ORDER.nightly run 20261018T090000Z-aaaaaa parked at 2-gate: red",
                1,
            ),
        ]
        for case, document, expected_text, expected_exit_code in rows:
            with self.subTest(case=case):
                # Act
                text = COMMAND.render_text(document)

                # Assert
                self.assertEqual(text, expected_text)
                self.assertEqual(COMMAND.decide_exit_code(document), expected_exit_code)
