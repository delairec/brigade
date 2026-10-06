from pathlib import Path

from brigade.runs.run_locations import PID_FILE
from brigade.system.write_text_atomically import write_text_atomically


def record_run_pid(run_directory: Path, pid: int) -> None:
    write_text_atomically(run_directory / PID_FILE, f"{pid}\n")
