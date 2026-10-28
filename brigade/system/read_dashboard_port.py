from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.name_toml_type import name_toml_type

DASHBOARD_PORT_KEY = "dashboard_port"
DASHBOARD_PORT_BY_DEFAULT = 8470
FIRST_PORT = 1
LAST_PORT = 65535


def read_dashboard_port(document: dict, path: Path) -> int:
    value = document.get(DASHBOARD_PORT_KEY, DASHBOARD_PORT_BY_DEFAULT)
    if isinstance(value, bool) or not isinstance(value, int):
        raise BrigadeError(f"{DASHBOARD_PORT_KEY} is {name_toml_type(value)}, not an integer, in {path}")
    if not FIRST_PORT <= value <= LAST_PORT:
        raise BrigadeError(f"{DASHBOARD_PORT_KEY} is {value}, not a port from {FIRST_PORT} to {LAST_PORT}, in {path}")
    return value
