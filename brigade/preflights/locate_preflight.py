from importlib.resources.abc import Traversable

from brigade.errors import BrigadeError

PREFLIGHT_SUFFIX = ".toml"


def locate_preflight(name: str, preflights: Traversable) -> Traversable:
    file = preflights / f"{name}{PREFLIGHT_SUFFIX}"
    if not file.is_file():
        raise BrigadeError(f"no preflight {name}: no {name}{PREFLIGHT_SUFFIX} in {preflights}")
    return file
