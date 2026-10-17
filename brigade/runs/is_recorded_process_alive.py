from pathlib import Path

from brigade.runs.read_run_pid import read_run_pid
from brigade.system.read_process_identity import read_process_identity


def is_recorded_process_alive(run_directory: Path) -> bool:
    recorded = read_run_pid(run_directory)
    return recorded is not None and read_process_identity(recorded.pid) == recorded.identity
