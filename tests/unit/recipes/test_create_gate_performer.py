import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.preflights.run_preflight import PreflightOutcome
from brigade.recipes.create_gate_performer import create_gate_performer
from brigade.recipes.run_order import OrderRun

NIGHTLY_RUN = OrderRun(
    order="nightly", project="shop", recipe={}, run_id="20261019T090000Z-aaaaaa", run_directory=Path("/srv/runs")
)
WAVE_GATE = {"kind": "gate", "preflight": "wave"}
GREEN_CHECK = {"name": "ancestry", "verdict": "pass", "findings": []}
ORDER_VALUES = {"pr": "12", "project": "shop"}
REVIEWED_GATE = {"kind": "gate", "preflight": "pr-reviewed", "parameters": {"pr": "{pr}"}}
RED_CHECK = {"name": "acceptance", "verdict": "fail", "findings": ["make test exited 2", "coverage under 90"]}


class GateDouble:
    def __init__(self, outcome: PreflightOutcome):
        self.outcome = outcome
        self.preflights_run: list[tuple[str, dict]] = []

    def run(self, name: str, parameters: dict) -> PreflightOutcome:
        self.preflights_run.append((name, parameters))
        return self.outcome


class CreateGatePerformerTest(unittest.TestCase):
    def test_should_pass_the_step_on_a_preflight_that_passed_and_keep_its_checks(self):
        # Arrange
        gate = GateDouble(PreflightOutcome(verdict="pass", checks=[GREEN_CHECK], collected={}))
        perform = create_gate_performer(gate.run, ORDER_VALUES)

        # Act
        result = perform(WAVE_GATE, NIGHTLY_RUN)

        # Assert
        self.assertEqual(result, {"preflight": "wave", "verdict": "pass", "checks": [GREEN_CHECK]})
        self.assertEqual(gate.preflights_run, [("wave", {})])

    def test_should_fail_the_step_on_a_preflight_that_failed_with_the_findings_of_its_failed_checks(self):
        # Arrange
        gate = GateDouble(PreflightOutcome(verdict="fail", checks=[GREEN_CHECK, RED_CHECK], collected={}))
        perform = create_gate_performer(gate.run, ORDER_VALUES)

        # Act
        with self.assertRaises(BrigadeError) as failure:
            perform(WAVE_GATE, NIGHTLY_RUN)

        # Assert
        self.assertEqual(
            str(failure.exception),
            "the preflight wave failed: acceptance: make test exited 2; coverage under 90",
        )

    def test_should_hand_the_preflight_the_parameters_of_the_step_filled_from_the_values_of_the_order(self):
        # Arrange
        gate = GateDouble(PreflightOutcome(verdict="pass", checks=[GREEN_CHECK], collected={}))
        perform = create_gate_performer(gate.run, ORDER_VALUES)

        # Act
        perform(REVIEWED_GATE, NIGHTLY_RUN)

        # Assert
        self.assertEqual(gate.preflights_run, [("pr-reviewed", {"pr": "12"})])
