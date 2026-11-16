import json
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.studies.study_run_context import STEPS_DIRECTORY

STEP_FILE_PATTERN = "*.json"
COLLECT_STEP_FILE_PATTERN = "*-collect.json"
RANK_SEPARATOR = "-"


def _read_rank(step_file: Path) -> int:
    return int(step_file.name.partition(RANK_SEPARATOR)[0])


def read_collected(run_directory: Path) -> list[dict]:
    steps = run_directory / STEPS_DIRECTORY
    if not any(steps.glob(STEP_FILE_PATTERN)):
        raise BrigadeError(f"the run {run_directory.name} has collected no evidence yet")
    return [
        entry
        for step_file in sorted(steps.glob(COLLECT_STEP_FILE_PATTERN), key=_read_rank)
        for entry in json.loads(step_file.read_text(encoding="utf-8"))["collected"]
    ]
