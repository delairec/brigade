from brigade.inbox.read_inbox import Signal
from brigade.waves.find_last_task_event import find_last_task_event
from brigade.waves.read_task_state import TASK_EVENTS, read_task_state

STALL_KIND = "stall"
MERGED_STATE = "merged"


def is_stall_stale(signal: Signal, events: tuple) -> bool:
    if signal.kind != STALL_KIND:
        return False
    last = find_last_task_event(events, TASK_EVENTS, signal.evidence["wave"], signal.evidence["task"])
    return last is not None and read_task_state(last) == MERGED_STATE
