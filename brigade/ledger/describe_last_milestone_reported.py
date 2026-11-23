from brigade.ledger.format_instant import format_instant
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.milestone_closed import MilestoneClosed
from brigade.ledger.milestone_reported import MilestoneReported


def describe_last_milestone_reported(entries: tuple[LedgerEntry, ...]) -> dict | None:
    reported = [index for index, entry in enumerate(entries) if isinstance(entry.event, MilestoneReported)]
    if not reported:
        return None
    last = entries[reported[-1]]
    project, milestone = last.event.project, last.event.milestone
    reached = [
        format_instant(entry.instant)
        for entry in entries[reported[-1] :]
        if isinstance(entry.event, MilestoneClosed)
        and (entry.event.project, entry.event.milestone) == (project, milestone)
    ]
    return {
        "project": project,
        "milestone": milestone,
        "report": f"{project}_{milestone}",
        "reported_at": format_instant(last.instant),
        "reached_main_at": reached[0] if reached else None,
    }
