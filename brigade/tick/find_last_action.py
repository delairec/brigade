from datetime import datetime

from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.run_finished import RunFinished
from brigade.ledger.task_state import TaskState
from brigade.ledger.tick_action_failed import TickActionFailed
from brigade.ledger.wave_started import WaveStarted

ACTIONS_ON_A_TASK = (TaskState, RunFinished, TickActionFailed)


def _is_action_on(entry: LedgerEntry, wave: str, task: str) -> bool:
    if isinstance(entry.event, WaveStarted):
        return entry.event.wave == wave
    return isinstance(entry.event, ACTIONS_ON_A_TASK) and (entry.event.wave, entry.event.task) == (wave, task)


def find_last_action(entries: tuple[LedgerEntry, ...], wave: str, task: str) -> datetime:
    return max(entry.instant for entry in entries if _is_action_on(entry, wave, task))
