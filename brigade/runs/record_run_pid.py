from pathlib import Path

from brigade.errors import BrigadeError
from brigade.runs.run_locations import PID_FILE
from brigade.system.read_process_identity import read_process_identity
from brigade.system.write_text_atomically import write_text_atomically


def record_run_pid(run_directory: Path, pid: int) -> None:
    identity = read_process_identity(pid)
    if identity is None:
        raise BrigadeError(f"no process holds pid {pid}")
    write_text_atomically(run_directory / PID_FILE, f"{pid} {identity}\n")
