from brigade.ledger.run_finished import RunFinished

AUTHENTICATION = "authentication"
REBASE_SLOT = "rebase"
DONE_OUTCOME = "done"


def is_rebase_done(events: tuple, run: dict) -> bool:
    finished = [event for event in events if isinstance(event, RunFinished) and event.run == run["run"]]
    return run["slot"] == REBASE_SLOT and bool(finished) and finished[-1].outcome == DONE_OUTCOME


def is_rebased_by_last_run(events: tuple, runs: tuple[dict, ...], wave: str, task: str) -> bool:
    naming = [run for run in runs if run["wave"] == wave and run["task"] == task]
    return bool(naming) and is_rebase_done(events, naming[-1])


def is_stopped_by_login(events: tuple, wave: str, task: str) -> bool:
    finished = [
        event for event in events if isinstance(event, RunFinished) and event.wave == wave and event.task == task
    ]
    return bool(finished) and finished[-1].error_class == AUTHENTICATION
