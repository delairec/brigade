import json
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.studies.study_run_context import STEPS_DIRECTORY

COLLECT_STEP_FILE = "collect.json"


def read_collected(run_directory: Path) -> list[dict]:
    try:
        step = json.loads((run_directory / STEPS_DIRECTORY / COLLECT_STEP_FILE).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise BrigadeError(f"the run {run_directory.name} has collected no evidence yet") from None
    return step["collected"]
