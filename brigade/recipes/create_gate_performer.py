from collections.abc import Callable

from brigade.errors import BrigadeError
from brigade.preflights.run_preflight import PreflightOutcome
from brigade.recipes.run_order import OrderRun, StepPerformer
from brigade.system.check_shapes import FAILED


def _describe_failed_checks(checks: list) -> str:
    return ", ".join(
        f"{check['name']}: {'; '.join(check['findings'])}" for check in checks if check["verdict"] == FAILED
    )


def create_gate_performer(run_gate: Callable[[str], PreflightOutcome]) -> StepPerformer:
    def perform(step: dict, run: OrderRun) -> dict:
        outcome = run_gate(step["preflight"])
        if outcome.verdict == FAILED:
            raise BrigadeError(f"the preflight {step['preflight']} failed: {_describe_failed_checks(outcome.checks)}")
        return {"preflight": step["preflight"], "verdict": outcome.verdict, "checks": outcome.checks}

    return perform
