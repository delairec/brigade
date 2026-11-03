from collections.abc import Iterable

MILESTONE_REPORTED = "milestone.reported"


def select_reported_milestones(events: Iterable[dict]) -> list[dict]:
    return [event for event in events if event["event"] == MILESTONE_REPORTED]
