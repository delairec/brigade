from brigade.ledger.ledger_entry import LedgerEntry
from brigade.waves.read_task_state import TASK_EVENTS, read_task_state


def read_task_states(entries: tuple[LedgerEntry, ...], wave: str) -> dict[str, str]:
    return {
        entry.event.task: read_task_state(entry.event)
        for entry in entries
        if isinstance(entry.event, TASK_EVENTS) and entry.event.wave == wave
    }
