from collections.abc import Callable

from brigade.errors import BrigadeError

HELD_BY_NO_PLACE = None


def find_preflight(name: str, places: tuple[Callable[[str], dict | None], ...]) -> dict:
    held = (preflight for preflight in (read(name) for read in places) if preflight is not None)
    preflight = next(held, HELD_BY_NO_PLACE)
    if preflight is HELD_BY_NO_PLACE:
        raise BrigadeError(
            f"no preflight {name} in the project, in the machine's preflights directory or among the built-ins"
        )
    return preflight
