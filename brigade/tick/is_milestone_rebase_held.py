from dataclasses import dataclass

from brigade.ledger.milestone_rebase_launched import MilestoneRebaseLaunched


@dataclass(frozen=True)
class MilestoneHeads:
    main: str | None
    branch: str | None


def is_milestone_rebase_held(events: tuple, run: str, heads: MilestoneHeads) -> bool:
    return any(
        isinstance(event, MilestoneRebaseLaunched)
        and event.run == run
        and (event.main_head, event.branch_head) == (heads.main, heads.branch)
        for event in events
    )
