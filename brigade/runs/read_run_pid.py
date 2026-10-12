from pathlib import Path

from brigade.runs.run_locations import PID_FILE


def read_run_pid(run_directory: Path) -> int | None:
    try:
        text = (run_directory / PID_FILE).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    if not text.isdigit():
        return None
    return int(text)
