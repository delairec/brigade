from typing import Optional, Tuple

PYTHON_FLOOR = (3, 11)


def describe_python_floor_breach(version: Tuple[int, ...]) -> Optional[str]:
    if tuple(version) >= PYTHON_FLOOR:
        return None
    floor = ".".join(str(part) for part in PYTHON_FLOOR)
    running = ".".join(str(part) for part in version)
    return "brigade needs Python {} or later; this is Python {}".format(floor, running)
