from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.name_toml_type import name_toml_type

TRAIL_DAYS_KEY = "trail_days"
TRAIL_DAYS_BY_DEFAULT = 7
FEWEST_TRAIL_DAYS = 1


def read_trail_days(document: dict, path: Path) -> int:
    value = document.get(TRAIL_DAYS_KEY, TRAIL_DAYS_BY_DEFAULT)
    if isinstance(value, bool) or not isinstance(value, int):
        raise BrigadeError(f"{TRAIL_DAYS_KEY} is {name_toml_type(value)}, not an integer, in {path}")
    if value < FEWEST_TRAIL_DAYS:
        raise BrigadeError(f"{TRAIL_DAYS_KEY} is {value}, not {FEWEST_TRAIL_DAYS} or more, in {path}")
    return value
