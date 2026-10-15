from pathlib import Path

from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.task_state import TaskState


def read_task_states(state_root: Path, wave: str) -> dict[str, str]:
    return {
        entry.event.task: entry.event.state
        for entry in read_ledger(state_root).entries
        if isinstance(entry.event, TaskState) and entry.event.wave == wave
    }
