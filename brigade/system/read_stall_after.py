from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.name_toml_type import name_toml_type

STALL_AFTER_KEY = "stall_after"
STALL_AFTER_BY_DEFAULT_MIN = 60
FEWEST_STALL_MINUTES = 1


def read_stall_after(document: dict, path: Path) -> int:
    value = document.get(STALL_AFTER_KEY, STALL_AFTER_BY_DEFAULT_MIN)
    if isinstance(value, bool) or not isinstance(value, int):
        raise BrigadeError(f"{STALL_AFTER_KEY} is {name_toml_type(value)}, not an integer, in {path}")
    if value < FEWEST_STALL_MINUTES:
        raise BrigadeError(f"{STALL_AFTER_KEY} is {value}, not {FEWEST_STALL_MINUTES} or more, in {path}")
    return value
