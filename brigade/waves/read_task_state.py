from brigade.ledger.task_parked import TaskParked
from brigade.ledger.task_state import TaskState

PARKED_STATE = "parked"
TASK_EVENTS = (TaskState, TaskParked)


def read_task_state(event: TaskState | TaskParked) -> str:
    if isinstance(event, TaskParked):
        return PARKED_STATE
    return event.state
