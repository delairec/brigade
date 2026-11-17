import json
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.orders.start_order_run import ORDER_RECORD_FILE
from brigade.studies.read_study_recipe import COLLECT_KIND
from brigade.studies.study_run_context import STEPS_DIRECTORY

STEP_FILE_PATTERN = "*.json"
COLLECT_STEP_FILE_PATTERN = f"*-{COLLECT_KIND}.json"
RANK_SEPARATOR = "-"
RECIPE_KEY = "recipe"


def _read_rank(step_file: Path) -> int:
    return int(step_file.name.partition(RANK_SEPARATOR)[0])


def _awaits_evidence(run_directory: Path) -> bool:
    record = run_directory / ORDER_RECORD_FILE
    if not record.is_file():
        return True
    recipe = json.loads(record.read_text(encoding="utf-8")).get(RECIPE_KEY)
    return recipe is None or any(step["kind"] == COLLECT_KIND for step in recipe["steps"])


def read_collected(run_directory: Path) -> list[dict]:
    steps = run_directory / STEPS_DIRECTORY
    if _awaits_evidence(run_directory) and not any(steps.glob(STEP_FILE_PATTERN)):
        raise BrigadeError(f"the run {run_directory.name} has collected no evidence yet")
    return [
        entry
        for step_file in sorted(steps.glob(COLLECT_STEP_FILE_PATTERN), key=_read_rank)
        for entry in json.loads(step_file.read_text(encoding="utf-8"))["collected"]
    ]
