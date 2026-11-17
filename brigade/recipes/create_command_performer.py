from collections.abc import Callable, Mapping
from pathlib import Path

from brigade.recipes.lint_recipe import PLACEHOLDER
from brigade.recipes.run_order import OrderRun, StepPerformer
from brigade.system.run_process import ProcessRecord, ProcessRequest

COMMAND_TIMEOUT_S = 3600


def create_command_performer(
    run_process: Callable[[ProcessRequest], ProcessRecord], directory: Path, values: Mapping[str, str]
) -> StepPerformer:
    def perform(step: dict, run: OrderRun) -> dict:
        argv = tuple(PLACEHOLDER.sub(lambda match: values[match.group(1)], argument) for argument in step["argv"])
        record = run_process(ProcessRequest(argv=argv, cwd=str(directory), timeout_s=COMMAND_TIMEOUT_S))
        return {"argv": list(argv), "exit_code": record.exit_code, "stdout": record.stdout}

    return perform
