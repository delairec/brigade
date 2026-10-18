from brigade.ledger.run_finished import RunFinished


def find_last_task_run(events: tuple, project: str, task: str) -> str | None:
    runs = [
        event.run
        for event in events
        if isinstance(event, RunFinished) and event.project == project and event.task == task
    ]
    return runs[-1] if runs else None
