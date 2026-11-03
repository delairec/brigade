from collections.abc import Iterable

TASK_REPORTED = "task.reported"


def select_reported_tasks(events: Iterable[dict]) -> list[dict]:
    return [event for event in events if event["event"] == TASK_REPORTED]
