def find_last_task_event(events: tuple, kind: type, wave: str, task: str) -> object | None:
    matching = [event for event in events if isinstance(event, kind) and event.wave == wave and event.task == task]
    return matching[-1] if matching else None
