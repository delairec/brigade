from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.name_toml_type import name_toml_type

RUNS_KEPT_KEY = "runs_kept"
RUNS_KEPT_BY_DEFAULT = 100
FEWEST_RUNS_KEPT = 1


def read_runs_kept(document: dict, path: Path) -> int:
    value = document.get(RUNS_KEPT_KEY, RUNS_KEPT_BY_DEFAULT)
    if isinstance(value, bool) or not isinstance(value, int):
        raise BrigadeError(f"{RUNS_KEPT_KEY} is {name_toml_type(value)}, not an integer, in {path}")
    if value < FEWEST_RUNS_KEPT:
        raise BrigadeError(f"{RUNS_KEPT_KEY} is {value}, not {FEWEST_RUNS_KEPT} or more, in {path}")
    return value
