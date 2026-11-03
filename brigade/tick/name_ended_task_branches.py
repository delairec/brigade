from brigade.ledger.ledger_entry import LedgerEntry
from brigade.tick.name_task_branch import name_task_branch
from brigade.waves.summarize_waves import summarize_waves


def name_ended_task_branches(entries: tuple[LedgerEntry, ...], project: str, task: str) -> frozenset[str]:
    return frozenset(
        name_task_branch(summary.started.branch, task)
        for summary in summarize_waves(entries)
        if not summary.is_open and summary.started.project == project
    )
