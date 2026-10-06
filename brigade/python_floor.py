from __future__ import annotations

PYTHON_FLOOR = (3, 11)


def describe_python_floor_breach(version: tuple[int, ...]) -> str | None:
    if tuple(version) >= PYTHON_FLOOR:
        return None
    floor = ".".join(str(part) for part in PYTHON_FLOOR)
    running = ".".join(str(part) for part in version)
    return f"brigade needs Python {floor} or later; this is Python {running}"
