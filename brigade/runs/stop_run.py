import os
import signal
import time
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.runs.describe_run import describe_run
from brigade.runs.read_run_pid import read_run_pid
from brigade.runs.run_locations import RUNS_DIRECTORY
from brigade.runs.show_run import show_run
from brigade.system.is_process_alive import is_process_alive

FINISHED = "finished"
STOPPED = "stopped"
STOP_POLL_S = 0.1


def _send_stop_signal(run_id: str, pid: int) -> None:
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        raise BrigadeError(f"run {run_id} is dead: no process holds its pid {pid}") from None


def stop_run(state_root: Path, run_id: str) -> dict:
    run = show_run(state_root, run_id, with_journal=False)["run"]
    if run["state"] == FINISHED:
        raise BrigadeError(f"run {run_id} has already finished on {run['outcome']}")
    run_directory = state_root / RUNS_DIRECTORY / run_id
    pid = read_run_pid(run_directory)
    if pid is None:
        raise BrigadeError(f"run {run_id} holds no pid file")
    _send_stop_signal(run_id, pid)
    while is_process_alive(pid):
        time.sleep(STOP_POLL_S)
    ended = describe_run(run_directory)
    if ended["outcome"] != STOPPED:
        raise BrigadeError(f"run {run_id} ended {ended['state']}, not stopped")
    return ended
