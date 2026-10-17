from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.name_toml_type import name_toml_type

STUDY_RUNS_KEY = "study_runs"
STUDY_RUNS_BY_DEFAULT = 2
FEWEST_STUDY_RUNS = 1


def read_study_runs(document: dict, path: Path) -> int:
    value = document.get(STUDY_RUNS_KEY, STUDY_RUNS_BY_DEFAULT)
    if isinstance(value, bool) or not isinstance(value, int):
        raise BrigadeError(f"{STUDY_RUNS_KEY} is {name_toml_type(value)}, not an integer, in {path}")
    if value < FEWEST_STUDY_RUNS:
        raise BrigadeError(f"{STUDY_RUNS_KEY} is {value}, not {FEWEST_STUDY_RUNS} or more, in {path}")
    return value
