from collections.abc import Iterable

MILESTONE_EVENTS = ("milestone.branch_cut", "milestone.pr_opened", "milestone.pr_described", "milestone.closed")


def select_milestone_events(events: Iterable[dict]) -> list[dict]:
    return [event for event in events if event["event"] in MILESTONE_EVENTS]
