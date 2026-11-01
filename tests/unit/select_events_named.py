from collections.abc import Iterable


def select_events_named(events: Iterable[dict], name: str) -> list[dict]:
    return [event for event in events if event["event"] == name]
