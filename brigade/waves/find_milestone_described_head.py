from brigade.ledger.milestone_pr_described import MilestonePrDescribed


def find_milestone_described_head(events: tuple, project: str, milestone: str, pr: int) -> str | None:
    heads = [
        event.head
        for event in events
        if isinstance(event, MilestonePrDescribed)
        and event.project == project
        and event.milestone == milestone
        and event.pr == pr
    ]
    return heads[-1] if heads else None
