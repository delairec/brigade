from collections.abc import Callable, Mapping
from pathlib import Path

from brigade.collecting.collect_document import Collection
from brigade.recipes.lint_recipe import PARAMETERS_KEY, PLACEHOLDER
from brigade.recipes.run_order import FIRST_STEP, OrderRun, StepPerformer

COLLECTORS_DIRECTORY = "collectors"
NO_PARAMETERS = {}


def _locate_place(step: dict, run: OrderRun) -> Path:
    rank = run.recipe["steps"].index(step) + FIRST_STEP
    return run.run_directory / COLLECTORS_DIRECTORY / str(rank)


def create_collect_performer(
    collect: Callable[[str, Mapping[str, str], Path], Collection], values: Mapping[str, str]
) -> StepPerformer:
    def perform(step: dict, run: OrderRun) -> dict:
        parameters = {
            key: PLACEHOLDER.sub(lambda match: values[match.group(1)], value)
            for key, value in step.get(PARAMETERS_KEY, NO_PARAMETERS).items()
        }
        collection = collect(step["collector"], parameters, _locate_place(step, run))
        return {
            "collector": step["collector"],
            "summary": collection.document["summary"],
            "document": str(collection.document_path),
        }

    return perform
