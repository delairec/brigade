import dataclasses
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.order_done import OrderDone
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.step_done import StepDone
from brigade.ledger.step_failed import StepFailed
from brigade.recipes.run_order import OrderRun, run_order
from tests.list_entry_names import list_entry_names
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import FIXED_NOW, create_test_runtime

RUN_ID = "20261019T090000Z-aaaaaa"
PAST_THE_WALL = datetime(2026, 10, 19, 9, 31, tzinfo=UTC)


class StepsDouble:
    def __init__(self, failures: dict[str, int]):
        self.failures = dict(failures)
        self.performed: list[str] = []

    def perform(self, step: dict, run: OrderRun) -> dict:
        self.performed.append(step["kind"])
        if self.failures.get(step["kind"], 0) > 0:
            self.failures[step["kind"]] -= 1
            raise BrigadeError(f"the {step['kind']} step failed")
        return {"kind": step["kind"]}

    def create_performers(self) -> dict:
        return {"collect": self.perform, "gate": self.perform, "command": self.perform, "output": self.perform}


def create_recipe(*steps: dict) -> dict:
    return {
        "schema_version": 1,
        "name": "usage-report",
        "description": "the usage report of a pull request",
        "params": [],
        "max_wall": 30,
        "steps": list(steps),
    }


COLLECT = {"kind": "collect", "collector": "pull-request"}
OUTPUT = {"kind": "output", "output": "inbox"}
GATE = {"kind": "gate", "preflight": "wave"}


class RunOrderTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.runtime = create_test_runtime(create_test_paths(self.root))
        self.run_directory = self.root / "state" / "runs" / RUN_ID
        self.steps_directory = self.run_directory / "steps"

    def create_run(self, recipe: dict) -> OrderRun:
        return OrderRun(order="nightly", project="shop", recipe=recipe, run_id=RUN_ID, run_directory=self.run_directory)

    def test_should_run_an_order_to_its_output(self):
        # Arrange
        steps = StepsDouble(failures={})

        # Act
        ran = run_order(self.runtime, self.create_run(create_recipe(COLLECT, OUTPUT)), steps.create_performers())

        # Assert
        self.assertEqual(ran, {"order": "nightly", "run": RUN_ID, "state": "done"})

    def test_should_keep_the_result_of_each_step_in_a_file_of_the_run(self):
        # Arrange
        steps = StepsDouble(failures={})

        # Act
        run_order(self.runtime, self.create_run(create_recipe(COLLECT, OUTPUT)), steps.create_performers())

        # Assert
        self.assertEqual(list_entry_names(self.steps_directory), ["1-collect.json", "2-output.json"])

    def test_should_record_each_step_and_the_order_done_under_the_name_of_the_recipe(self):
        # Arrange
        steps = StepsDouble(failures={})

        # Act
        run_order(self.runtime, self.create_run(create_recipe(COLLECT, OUTPUT)), steps.create_performers())

        # Assert
        self.assertEqual(
            read_ledger(self.root / "state").entries,
            (
                LedgerEntry(instant=FIXED_NOW, event=StepDone(kind="usage-report", run=RUN_ID, step="1-collect")),
                LedgerEntry(instant=FIXED_NOW, event=StepDone(kind="usage-report", run=RUN_ID, step="2-output")),
                LedgerEntry(
                    instant=FIXED_NOW,
                    event=OrderDone(project="shop", kind="usage-report", order="nightly", run=RUN_ID),
                ),
            ),
        )

    def test_should_not_run_again_a_step_whose_file_exists(self):
        # Arrange
        self.steps_directory.mkdir(parents=True)
        (self.steps_directory / "1-collect.json").write_text('{"kind": "collect"}', encoding="utf-8")
        steps = StepsDouble(failures={})

        # Act
        run_order(self.runtime, self.create_run(create_recipe(COLLECT, OUTPUT)), steps.create_performers())

        # Assert
        self.assertEqual(steps.performed, ["output"])

    def test_should_park_the_order_on_the_reason_of_a_failed_gate(self):
        # Arrange
        steps = StepsDouble(failures={"gate": 1})

        # Act
        ran = run_order(self.runtime, self.create_run(create_recipe(GATE, OUTPUT)), steps.create_performers())

        # Assert
        self.assertEqual(
            ran,
            {"order": "nightly", "run": RUN_ID, "state": "parked", "step": "1-gate", "reason": "the gate step failed"},
        )

    def test_should_record_the_failed_step_and_the_order_parked(self):
        # Arrange
        steps = StepsDouble(failures={"gate": 1})

        # Act
        run_order(self.runtime, self.create_run(create_recipe(GATE, OUTPUT)), steps.create_performers())

        # Assert
        self.assertEqual(
            read_ledger(self.root / "state").entries,
            (
                LedgerEntry(
                    instant=FIXED_NOW,
                    event=StepFailed(kind="usage-report", run=RUN_ID, step="1-gate", reason="the gate step failed"),
                ),
                LedgerEntry(
                    instant=FIXED_NOW,
                    event=OrderParked(
                        project="shop",
                        kind="usage-report",
                        order="nightly",
                        run=RUN_ID,
                        step="1-gate",
                        reason="the gate step failed",
                    ),
                ),
            ),
        )

    def test_should_run_no_step_past_the_one_that_parked_the_order(self):
        # Arrange
        steps = StepsDouble(failures={"gate": 1})

        # Act
        run_order(self.runtime, self.create_run(create_recipe(GATE, OUTPUT)), steps.create_performers())

        # Assert
        self.assertEqual(steps.performed, ["gate"])

    def test_should_go_on_past_a_failed_step_the_recipe_skips(self):
        # Arrange
        steps = StepsDouble(failures={"gate": 1})
        skipped_gate = {**GATE, "on_fail": "skip"}

        # Act
        ran = run_order(self.runtime, self.create_run(create_recipe(skipped_gate, OUTPUT)), steps.create_performers())

        # Assert
        self.assertEqual(ran, {"order": "nightly", "run": RUN_ID, "state": "done"})

    def test_should_not_run_again_a_step_the_recipe_skipped(self):
        # Arrange
        steps = StepsDouble(failures={"gate": 1})
        skipped_gate = {**GATE, "on_fail": "skip"}

        # Act
        run_order(self.runtime, self.create_run(create_recipe(skipped_gate, OUTPUT)), steps.create_performers())

        # Assert
        self.assertEqual(list_entry_names(self.steps_directory), ["1-gate.json", "2-output.json"])

    def test_should_record_a_skipped_step_failed_and_never_done(self):
        # Arrange
        steps = StepsDouble(failures={"gate": 1})
        skipped_gate = {**GATE, "on_fail": "skip"}

        # Act
        run_order(self.runtime, self.create_run(create_recipe(skipped_gate)), steps.create_performers())

        # Assert
        self.assertEqual(
            read_ledger(self.root / "state").entries,
            (
                LedgerEntry(
                    instant=FIXED_NOW,
                    event=StepFailed(kind="usage-report", run=RUN_ID, step="1-gate", reason="the gate step failed"),
                ),
                LedgerEntry(
                    instant=FIXED_NOW,
                    event=OrderDone(project="shop", kind="usage-report", order="nightly", run=RUN_ID),
                ),
            ),
        )

    def test_should_end_the_order_without_parking_it_on_a_failed_step_the_recipe_stops_at(self):
        # Arrange
        steps = StepsDouble(failures={"gate": 1})
        stopping_gate = {**GATE, "on_fail": "stop"}

        # Act
        ran = run_order(self.runtime, self.create_run(create_recipe(stopping_gate, OUTPUT)), steps.create_performers())

        # Assert
        self.assertEqual(
            ran,
            {"order": "nightly", "run": RUN_ID, "state": "stopped", "step": "1-gate", "reason": "the gate step failed"},
        )

    def test_should_record_the_order_done_once_a_failed_step_stops_it(self):
        # Arrange
        steps = StepsDouble(failures={"gate": 1})
        stopping_gate = {**GATE, "on_fail": "stop"}

        # Act
        run_order(self.runtime, self.create_run(create_recipe(stopping_gate, OUTPUT)), steps.create_performers())

        # Assert
        self.assertEqual(
            read_ledger(self.root / "state").entries[-1],
            LedgerEntry(
                instant=FIXED_NOW, event=OrderDone(project="shop", kind="usage-report", order="nightly", run=RUN_ID)
            ),
        )

    def test_should_run_a_failed_step_again_as_many_times_as_the_recipe_retries_it(self):
        # Arrange
        steps = StepsDouble(failures={"command": 2})
        retried_command = {"kind": "command", "argv": ["make", "lint"], "on_fail": "retry:2"}

        # Act
        ran = run_order(self.runtime, self.create_run(create_recipe(retried_command)), steps.create_performers())

        # Assert
        self.assertEqual(ran, {"order": "nightly", "run": RUN_ID, "state": "done"})

    def test_should_park_the_order_once_its_retries_are_spent(self):
        # Arrange
        steps = StepsDouble(failures={"command": 3})
        retried_command = {"kind": "command", "argv": ["make", "lint"], "on_fail": "retry:2"}

        # Act
        ran = run_order(self.runtime, self.create_run(create_recipe(retried_command)), steps.create_performers())

        # Assert
        self.assertEqual(
            ran,
            {
                "order": "nightly",
                "run": RUN_ID,
                "state": "parked",
                "step": "1-command",
                "reason": "the command step failed",
            },
        )

    def test_should_park_a_run_past_the_max_wall_of_its_recipe(self):
        # Arrange
        steps = StepsDouble(failures={})
        runtime = dataclasses.replace(self.runtime, read_clock=lambda: PAST_THE_WALL)

        # Act
        ran = run_order(runtime, self.create_run(create_recipe(COLLECT, OUTPUT)), steps.create_performers())

        # Assert
        self.assertEqual(
            ran,
            {
                "order": "nightly",
                "run": RUN_ID,
                "state": "parked",
                "step": "1-collect",
                "reason": "the run passed the max_wall of 30 minutes of the recipe usage-report",
            },
        )
