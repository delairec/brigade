import argparse
from collections.abc import Callable

from brigade.errors import BrigadeError
from brigade.recipes.run_order import OrderRun, StepPerformer
from brigade.studies.study_run_context import ANSWER_FILE


def create_judge_performer(launch: Callable[[argparse.Namespace], dict]) -> StepPerformer:
    def perform(step: dict, run: OrderRun) -> dict:
        judging = argparse.Namespace(
            procedure=step["procedure"],
            slot=step["slot"],
            project=run.project,
            cwd=None,
            brief=None,
            arguments=(f"order={run.order}", f"run={run.run_id}"),
            run_id=None,
            wave=None,
            task=None,
            detach=False,
            resume=False,
        )
        launched = launch(judging)
        if not (run.run_directory / ANSWER_FILE).is_file():
            raise BrigadeError(f"the judging run {launched['run']} gave no answer")
        return {"run": launched["run"]}

    return perform
