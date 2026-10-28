from brigade.ledger.task_state import REQUEUE_REASON, TaskState


def is_requeue(event, wave: str) -> bool:
    return isinstance(event, TaskState) and event.wave == wave and event.reason == REQUEUE_REASON
