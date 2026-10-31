from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.milestone_branch_cut import MilestoneBranchCut

NOT_CUT = None


def find_milestone_branch(entries: tuple[LedgerEntry, ...], project: str, milestone: str | None) -> str | None:
    return next(
        (
            entry.event.branch
            for entry in reversed(entries)
            if isinstance(entry.event, MilestoneBranchCut)
            and entry.event.project == project
            and entry.event.milestone == milestone
        ),
        NOT_CUT,
    )
