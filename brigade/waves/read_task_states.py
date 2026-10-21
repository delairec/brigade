from pathlib import Path

from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.task_parked import TaskParked
from brigade.ledger.task_state import TaskState

PARKED_STATE = "parked"


def _read_state(event: TaskState | TaskParked) -> str:
    if isinstance(event, TaskParked):
        return PARKED_STATE
    return event.state


def read_task_states(state_root: Path, wave: str) -> dict[str, str]:
    return {
        entry.event.task: _read_state(entry.event)
        for entry in read_ledger(state_root).entries
        if isinstance(entry.event, (TaskState, TaskParked)) and entry.event.wave == wave
    }
