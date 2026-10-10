from __future__ import annotations

PYTHON_FLOOR = (3, 11, 4)


def refuse_python_below_floor(version: tuple[int, ...]) -> None:
    if tuple(version) >= PYTHON_FLOOR:
        return
    floor = ".".join(str(part) for part in PYTHON_FLOOR)
    running = ".".join(str(part) for part in version)
    raise SystemExit(f"brigade needs Python {floor} or later; this is Python {running}")
