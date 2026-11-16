import argparse
import contextlib
import functools
import json
import tempfile
import tomllib
import unittest
from pathlib import Path

from brigade.commands.order_run import COMMAND, order_run
from brigade.inbox.read_inbox import read_inbox
from brigade.ledger.append_event import append_event
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.order_done import OrderDone
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.order_started import OrderStarted
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.step_done import StepDone
from brigade.orders.convert_order import Order
from brigade.orders.start_order_run import start_order_run
from brigade.system.resolve_plugin import resolve_plugin
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import FIXED_NOW, create_test_runtime
from tests.unit.recipes.checkout_answers import create_checkout_answers
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers
from tests.unit.select_argvs_run_in import select_argvs_run_in
from tests.value_matchers import PatternMatcher

NO_PLUGIN_SOURCES = None
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
GATED = (
    'schema_version = 1\nname = "gated"\ndescription = "a gate before the report"\nparams = []\nmax_wall = 30\n'
    '[[steps]]\nkind = "gate"\npreflight = "quiet"\n'
)
QUIET = 'schema_version = 1\nname = "quiet"\ndescription = "no collector and no check"\ncollectors = []\nchecks = []\n'
GATED_ORDER = ProcessAnswer(
    stdout=json.dumps(
        {
            "fields": [
                {"name": "RECIPE", "atoms": ['"gated"']},
                {"name": "PROJECT", "atoms": ['"@PROJECT.shop"']},
                {"name": "STATUS", "atoms": ['"active"']},
            ]
        }
    )
)
COLLECTED = (
    'schema_version = 1\nname = "collected"\ndescription = "the open issues"\nparams = []\nmax_wall = 30\n'
    '[[steps]]\nkind = "collect"\ncollector = "open-issues"\n'
)
JUDGED = (
    'schema_version = 1\nname = "judged"\ndescription = "a judged triage"\nparams = []\nmax_wall = 30\n'
    '[[steps]]\nkind = "judge"\nslot = "judging"\nprocedure = "triage"\nanswer = "ANSWER"\n'
)
KEPT = (
    'schema_version = 1\nname = "kept"\ndescription = "the open issues, kept"\nparams = []\nmax_wall = 30\n'
    '[[steps]]\nkind = "collect"\ncollector = "open-issues"\n'
    '[[steps]]\nkind = "output"\noutput = "inbox"\n'
)
KEPT_ORDER = ProcessAnswer(
    stdout=json.dumps(
        {
            "fields": [
                {"name": "RECIPE", "atoms": ['"kept"']},
                {"name": "PROJECT", "atoms": ['"@PROJECT.shop"']},
                {"name": "OUTPUT", "atoms": ['"entity:RESULT"']},
                {"name": "STATUS", "atoms": ['"active"']},
            ]
        }
    )
)
OPEN_ISSUES = {
    "schema_version": 1,
    "collector": "open-issues",
    "collected_at": "2026-10-19T09:00:00Z",
    "cache": False,
    "summary": {"open": 2},
    "items": [],
}


def create_order_answer(recipe: str) -> ProcessAnswer:
    return ProcessAnswer(
        stdout=json.dumps(
            {
                "fields": [
                    {"name": "RECIPE", "atoms": [f'"{recipe}"']},
                    {"name": "PROJECT", "atoms": ['"@PROJECT.shop"']},
                    {"name": "STATUS", "atoms": ['"active"']},
                ]
            }
        )
    )


NEW_RUN = PatternMatcher("20261019T090000Z-[0-9a-f]{6}")
NIGHTLY_ORDER = Order(
    name="nightly",
    recipe="usage-report",
    project="shop",
    text=None,
    params=("pull_request=12",),
    every=None,
    output=None,
    status="active",
)


class OrderRunTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name).resolve()
        write_operational_corpus(root)
        self.paths = create_test_paths(root)
        (self.paths.config_root / "recipes").mkdir()
        (self.paths.config_root / "recipes" / "usage-report.toml").write_text(USAGE_REPORT, encoding="utf-8")
        (self.paths.config_root / "recipes" / "gated.toml").write_text(GATED, encoding="utf-8")
        (self.paths.config_root / "recipes" / "collected.toml").write_text(COLLECTED, encoding="utf-8")
        (self.paths.config_root / "recipes" / "judged.toml").write_text(JUDGED, encoding="utf-8")
        (self.paths.config_root / "recipes" / "kept.toml").write_text(KEPT, encoding="utf-8")
        (self.paths.config_root / "preflights").mkdir()
        (self.paths.config_root / "preflights" / "quiet.toml").write_text(QUIET, encoding="utf-8")
        self.shop = root / "shop"
        self.shop.mkdir()
        self.enterContext(contextlib.chdir(self.shop))
        collector = self.shop / ".brigade" / "collectors" / "open-issues"
        collector.parent.mkdir(parents=True)
        collector.write_text("#!/bin/sh\n", encoding="utf-8")
        collector.chmod(0o755)
        config = str(self.paths.config_root)
        self.runner = RecordingProcessRunner(
            {
                **create_registry_answers(self.paths.config_root, {"shop": {"PATH": str(self.shop), "MODE": "none"}}),
                **create_checkout_answers(self.shop, self.shop),
                ("awawa", "show", "@ORDER.nightly", "--json", config): NIGHTLY,
                ("awawa", "show", "@ORDER.gated", "--json", config): GATED_ORDER,
                ("awawa", "show", "@ORDER.collected", "--json", config): create_order_answer("collected"),
                ("awawa", "show", "@ORDER.judged", "--json", config): create_order_answer("judged"),
                ("awawa", "show", "@ORDER.kept", "--json", config): KEPT_ORDER,
                (str(collector),): ProcessAnswer(stdout=json.dumps(OPEN_ISSUES)),
            }
        )
        self.runtime = create_test_runtime(
            self.paths,
            run_process=self.runner,
            resolve_plugin=functools.partial(resolve_plugin, sources=NO_PLUGIN_SOURCES),
        )

    def test_should_run_the_steps_of_the_recipe_of_the_order_in_its_project(self):
        # Act
        document = order_run(argparse.Namespace(name="nightly", run_id=None), self.runtime)

        # Assert
        self.assertEqual(document, {"schema_version": 1, "order": "nightly", "run": NEW_RUN, "state": "done"})
        self.assertEqual(
            select_argvs_run_in(self.runner.requests, str(self.shop)),
            [("make", "collect", "PR=12"), ("make", "report", "shop")],
        )

    def test_should_run_the_run_the_tick_started_without_starting_another(self):
        # Arrange
        start_order_run(self.runtime, NIGHTLY_ORDER, tomllib.loads(USAGE_REPORT), "20261019T085500Z-cccccc")

        # Act
        document = order_run(argparse.Namespace(name="nightly", run_id="20261019T085500Z-cccccc"), self.runtime)

        # Assert
        self.assertEqual(
            document, {"schema_version": 1, "order": "nightly", "run": "20261019T085500Z-cccccc", "state": "done"}
        )
        self.assertEqual(
            read_ledger(self.paths.state_root).entries,
            (
                LedgerEntry(
                    instant=FIXED_NOW,
                    event=OrderStarted(
                        project="shop", kind="usage-report", order="nightly", run="20261019T085500Z-cccccc"
                    ),
                ),
                LedgerEntry(
                    instant=FIXED_NOW,
                    event=StepDone(kind="usage-report", run="20261019T085500Z-cccccc", step="1-command"),
                ),
                LedgerEntry(
                    instant=FIXED_NOW,
                    event=StepDone(kind="usage-report", run="20261019T085500Z-cccccc", step="2-command"),
                ),
                LedgerEntry(
                    instant=FIXED_NOW,
                    event=OrderDone(
                        project="shop", kind="usage-report", order="nightly", run="20261019T085500Z-cccccc"
                    ),
                ),
            ),
        )

    def test_should_record_the_run_of_the_order_under_the_name_of_its_recipe(self):
        # Act
        order_run(argparse.Namespace(name="nightly", run_id=None), self.runtime)

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

    def _park_after_its_first_step(self, recipe: dict) -> None:
        start_order_run(self.runtime, NIGHTLY_ORDER, recipe, PARKED_RUN)
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

    def test_should_resume_a_parked_order_at_its_first_undone_step(self):
        # Arrange
        self._park_after_its_first_step(tomllib.loads(USAGE_REPORT))

        # Act
        document = order_run(argparse.Namespace(name="nightly", run_id=None), self.runtime)

        # Assert
        self.assertEqual(document, {"schema_version": 1, "order": "nightly", "run": PARKED_RUN, "state": "done"})
        self.assertEqual(select_argvs_run_in(self.runner.requests, str(self.shop)), [("make", "report", "shop")])

    def test_should_resume_a_parked_order_with_the_recipe_its_run_recorded(self):
        # Arrange
        recorded = tomllib.loads(USAGE_REPORT)
        recorded["steps"][1]["argv"] = ["make", "summary", "{project}"]
        self._park_after_its_first_step(recorded)

        # Act
        order_run(argparse.Namespace(name="nightly", run_id=None), self.runtime)

        # Assert
        self.assertEqual(select_argvs_run_in(self.runner.requests, str(self.shop)), [("make", "summary", "shop")])

    def test_should_start_a_new_run_when_a_study_of_the_same_name_parked(self):
        # Arrange
        append_event(self.paths, FIXED_NOW, OrderStarted(project="shop", kind="study", order="nightly", run=PARKED_RUN))
        append_event(
            self.paths,
            FIXED_NOW,
            OrderParked(project="shop", kind="study", order="nightly", run=PARKED_RUN, step="judge", reason="red"),
        )

        # Act
        document = order_run(argparse.Namespace(name="nightly", run_id=None), self.runtime)

        # Assert
        self.assertEqual(document, {"schema_version": 1, "order": "nightly", "run": NEW_RUN, "state": "done"})

    def test_should_run_the_preflight_a_gate_step_names(self):
        # Act
        document = order_run(argparse.Namespace(name="gated", run_id=None), self.runtime)

        # Assert
        self.assertEqual(document, {"schema_version": 1, "order": "gated", "run": NEW_RUN, "state": "done"})

    def test_should_keep_the_document_of_the_collector_a_collect_step_names(self):
        # Act
        document = order_run(argparse.Namespace(name="collected", run_id=None), self.runtime)

        # Assert
        step_file = self.paths.state_root / "runs" / document["run"] / "steps" / "1-collect.json"
        self.assertEqual(
            json.loads(step_file.read_text(encoding="utf-8")),
            {
                "collector": "open-issues",
                "summary": {"open": 2},
                "document": str(
                    self.paths.state_root / "runs" / document["run"] / "collectors/1/collect/open-issues/document.json"
                ),
            },
        )

    def test_should_park_the_order_on_a_judging_run_that_cannot_start(self):
        # Act
        document = order_run(argparse.Namespace(name="judged", run_id=None), self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "order": "judged",
                "run": NEW_RUN,
                "state": "parked",
                "step": "1-judge",
                "reason": f"no configuration at {self.paths.config_root / 'config.toml'}; run brigade init",
            },
        )

    def test_should_signal_the_parked_order_in_the_inbox(self):
        # Act
        document = order_run(argparse.Namespace(name="judged", run_id=None), self.runtime)

        # Assert
        self.assertEqual(
            [
                (signal.kind, signal.project, signal.fingerprint, signal.evidence)
                for signal in read_inbox(self.paths.state_root, FIXED_NOW)
            ],
            [
                (
                    "order_parked",
                    "shop",
                    f"order_parked:judged:{document['run']}",
                    {
                        "order": "judged",
                        "recipe": "judged",
                        "run": document["run"],
                        "step": "1-judge",
                        "reason": f"no configuration at {self.paths.config_root / 'config.toml'}; run brigade init",
                    },
                )
            ],
        )

    def test_should_keep_the_result_of_the_order_and_hand_it_to_the_output_the_order_names(self):
        # Act
        document = order_run(argparse.Namespace(name="kept", run_id=None), self.runtime)

        # Assert
        run_directory = self.paths.state_root / "runs" / document["run"]
        step_file = run_directory / "steps" / "2-output.json"
        self.assertEqual(
            json.loads(step_file.read_text(encoding="utf-8")),
            {"output": "entity:RESULT", "answer": str(run_directory / "answer.awawa")},
        )
        self.assertIn(("git", "add", "--", "results.awawa"), self.runner.list_argvs())


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
