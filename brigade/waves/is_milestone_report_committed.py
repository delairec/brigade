from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.milestone_reported import MilestoneReported
from brigade.ledger.order_done import OrderDone


def is_milestone_report_committed(entries: tuple[LedgerEntry, ...], project: str, milestone: str | None) -> bool:
    runs = {
        entry.event.run
        for entry in entries
        if isinstance(entry.event, MilestoneReported)
        and (entry.event.project, entry.event.milestone) == (project, milestone)
    }
    return any(isinstance(entry.event, OrderDone) and entry.event.run in runs for entry in entries)
