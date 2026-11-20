from brigade.ledger.task_parked import TaskParked
from brigade.waves.find_last_task_event import find_last_task_event


def read_parked_reason(events: tuple, wave: str, task: str) -> str | None:
    parked = find_last_task_event(events, TaskParked, wave, task)
    return None if parked is None else parked.reason
