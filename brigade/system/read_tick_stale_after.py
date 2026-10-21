from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.name_toml_type import name_toml_type

TICK_STALE_AFTER_KEY = "tick_stale_after"
TICK_STALE_AFTER_BY_DEFAULT_MIN = 15
FEWEST_STALE_MINUTES = 1


def read_tick_stale_after(document: dict, path: Path) -> int:
    value = document.get(TICK_STALE_AFTER_KEY, TICK_STALE_AFTER_BY_DEFAULT_MIN)
    if isinstance(value, bool) or not isinstance(value, int):
        raise BrigadeError(f"{TICK_STALE_AFTER_KEY} is {name_toml_type(value)}, not an integer, in {path}")
    if value < FEWEST_STALE_MINUTES:
        raise BrigadeError(f"{TICK_STALE_AFTER_KEY} is {value}, not {FEWEST_STALE_MINUTES} or more, in {path}")
    return value
