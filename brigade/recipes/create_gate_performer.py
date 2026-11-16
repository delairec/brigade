from collections.abc import Callable, Mapping

from brigade.errors import BrigadeError
from brigade.preflights.run_preflight import PreflightOutcome
from brigade.recipes.lint_recipe import PARAMETERS_KEY, PLACEHOLDER
from brigade.recipes.run_order import OrderRun, StepPerformer
from brigade.system.check_shapes import FAILED

NO_PARAMETERS = {}


def _describe_failed_checks(checks: list) -> str:
    return ", ".join(
        f"{check['name']}: {'; '.join(check['findings'])}" for check in checks if check["verdict"] == FAILED
    )


def create_gate_performer(
    run_gate: Callable[[str, Mapping[str, str]], PreflightOutcome], values: Mapping[str, str]
) -> StepPerformer:
    def perform(step: dict, run: OrderRun) -> dict:
        parameters = {
            key: PLACEHOLDER.sub(lambda match: values[match.group(1)], value)
            for key, value in step.get(PARAMETERS_KEY, NO_PARAMETERS).items()
        }
        outcome = run_gate(step["preflight"], parameters)
        if outcome.verdict == FAILED:
            raise BrigadeError(f"the preflight {step['preflight']} failed: {_describe_failed_checks(outcome.checks)}")
        return {"preflight": step["preflight"], "verdict": outcome.verdict, "checks": outcome.checks}

    return perform
