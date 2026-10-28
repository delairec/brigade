from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.name_toml_type import name_toml_type

QUOTA_WINDOW_KEY = "quota_window_hours"
QUOTA_WINDOW_BY_DEFAULT_H = 5
FEWEST_WINDOW_HOURS = 1


def read_quota_window(document: dict, path: Path) -> int:
    value = document.get(QUOTA_WINDOW_KEY, QUOTA_WINDOW_BY_DEFAULT_H)
    if isinstance(value, bool) or not isinstance(value, int):
        raise BrigadeError(f"{QUOTA_WINDOW_KEY} is {name_toml_type(value)}, not an integer, in {path}")
    if value < FEWEST_WINDOW_HOURS:
        raise BrigadeError(f"{QUOTA_WINDOW_KEY} is {value}, not {FEWEST_WINDOW_HOURS} or more, in {path}")
    return value
