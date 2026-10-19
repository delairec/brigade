import os
import signal
import time
from pathlib import Path
from typing import NoReturn

from brigade.errors import BrigadeError
from brigade.runs.describe_run import describe_run
from brigade.runs.read_run_pid import RunProcess, read_run_pid
from brigade.runs.run_locations import RUNS_DIRECTORY
from brigade.runs.show_run import show_run
from brigade.system.is_catching_signal import is_catching_signal
from brigade.system.read_process_identity import read_process_identity

FINISHED = "finished"
STOPPED = "stopped"
STOP_POLL_S = 0.1
READY_WAIT_S = 10


def _holds_its_process(recorded: RunProcess) -> bool:
    return read_process_identity(recorded.pid) == recorded.identity


def _refuse_dead_run(run_id: str, pid: int) -> NoReturn:
    raise BrigadeError(f"run {run_id} is dead: no process of its identity holds its pid {pid}")


def _await_readiness(run_directory: Path, run_id: str) -> RunProcess:
    previous = None
    for _ in range(int(READY_WAIT_S / STOP_POLL_S)):
        recorded = read_run_pid(run_directory)
        if recorded is None:
            raise BrigadeError(f"run {run_id} holds no pid file naming its process")
        if _holds_its_process(recorded):
            if is_catching_signal(recorded.pid, signal.SIGTERM):
                return recorded
        elif recorded == previous:
            _refuse_dead_run(run_id, recorded.pid)
        previous = recorded
        time.sleep(STOP_POLL_S)
    raise BrigadeError(f"run {run_id} has not signalled it is ready within {READY_WAIT_S} s: no signal sent")


def stop_run(state_root: Path, run_id: str) -> dict:
    run = show_run(state_root, run_id, with_journal=False)["run"]
    if run["state"] == FINISHED:
        raise BrigadeError(f"run {run_id} has already finished on {run['outcome']}")
    run_directory = state_root / RUNS_DIRECTORY / run_id
    recorded = _await_readiness(run_directory, run_id)
    try:
        os.kill(recorded.pid, signal.SIGTERM)
    except ProcessLookupError:
        _refuse_dead_run(run_id, recorded.pid)
    while _holds_its_process(recorded):
        time.sleep(STOP_POLL_S)
    ended = describe_run(run_directory)
    if ended["outcome"] != STOPPED:
        raise BrigadeError(f"run {run_id} ended {ended['state']}, not stopped")
    return ended
