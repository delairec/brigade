from pathlib import Path
from typing import NamedTuple

from brigade.runs.run_locations import PID_FILE

PID_LINE_FIELDS = 3


class RunProcess(NamedTuple):
    pid: int
    identity: str


def read_run_pid(run_directory: Path) -> RunProcess | None:
    try:
        fields = (run_directory / PID_FILE).read_text(encoding="utf-8").split()
    except FileNotFoundError:
        return None
    if len(fields) != PID_LINE_FIELDS:
        return None
    pid, start_time, boot_id = fields
    if not (pid.isdigit() and start_time.isdigit()):
        return None
    return RunProcess(int(pid), f"{start_time} {boot_id}")
