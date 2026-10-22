from pathlib import Path

from brigade.ledger.read_ledger import read_ledger
from brigade.waves.read_task_state import TASK_EVENTS, read_task_state


def read_task_states(state_root: Path, wave: str) -> dict[str, str]:
    return {
        entry.event.task: read_task_state(entry.event)
        for entry in read_ledger(state_root).entries
        if isinstance(entry.event, TASK_EVENTS) and entry.event.wave == wave
    }
