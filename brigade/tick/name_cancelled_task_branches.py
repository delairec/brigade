from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.wave_cancelled import WaveCancelled
from brigade.tick.name_task_branch import name_task_branch
from brigade.waves.summarize_waves import summarize_waves


def name_cancelled_task_branches(entries: tuple[LedgerEntry, ...], project: str, task: str) -> frozenset[str]:
    return frozenset(
        name_task_branch(summary.started.branch, task)
        for summary in summarize_waves(entries)
        if summary.last_event == WaveCancelled.name and summary.started.project == project
    )
