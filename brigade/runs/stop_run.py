import os
import signal
import time
from collections.abc import Callable
from dataclasses import dataclass
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


@dataclass(frozen=True)
class StopEquipment:
    signal_process: Callable[[int, int], None]
    read_identity: Callable[[int], str | None]
    is_catching_signal: Callable[[int, int], bool]
    wait: Callable[[float], None]


SYSTEM_EQUIPMENT = StopEquipment(
    signal_process=os.kill,
    read_identity=read_process_identity,
    is_catching_signal=is_catching_signal,
    wait=time.sleep,
)


def _holds_its_process(recorded: RunProcess, equipment: StopEquipment) -> bool:
    return equipment.read_identity(recorded.pid) == recorded.identity


def _refuse_dead_run(run_id: str, pid: int) -> NoReturn:
    raise BrigadeError(f"run {run_id} is dead: no process of its identity holds its pid {pid}")


def _await_readiness(run_directory: Path, run_id: str, equipment: StopEquipment) -> RunProcess:
    previous = None
    for _ in range(int(READY_WAIT_S / STOP_POLL_S)):
        recorded = read_run_pid(run_directory)
        if recorded is None:
            raise BrigadeError(f"run {run_id} holds no pid file naming its process")
        if _holds_its_process(recorded, equipment):
            if equipment.is_catching_signal(recorded.pid, signal.SIGTERM):
                return recorded
        elif recorded == previous:
            _refuse_dead_run(run_id, recorded.pid)
        previous = recorded
        equipment.wait(STOP_POLL_S)
    raise BrigadeError(f"run {run_id} has not signalled it is ready within {READY_WAIT_S} s: no signal sent")


def stop_run(state_root: Path, run_id: str, equipment: StopEquipment) -> dict:
    run = show_run(state_root, run_id, with_journal=False)["run"]
    if run["state"] == FINISHED:
        raise BrigadeError(f"run {run_id} has already finished on {run['outcome']}")
    run_directory = state_root / RUNS_DIRECTORY / run_id
    recorded = _await_readiness(run_directory, run_id, equipment)
    try:
        equipment.signal_process(recorded.pid, signal.SIGTERM)
    except ProcessLookupError:
        _refuse_dead_run(run_id, recorded.pid)
    while _holds_its_process(recorded, equipment):
        equipment.wait(STOP_POLL_S)
    ended = describe_run(run_directory)
    if ended["outcome"] != STOPPED:
        raise BrigadeError(f"run {run_id} ended {ended['state']}, not stopped")
    return ended
