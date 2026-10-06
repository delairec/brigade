from datetime import datetime

from brigade.ledger.count_by_name import count_by_name
from brigade.ledger.format_instant import format_instant
from brigade.ledger.read_ledger import LedgerReading

COUNTED_EVENTS = {
    "waves_started": "wave.started",
    "pull_requests_merged": "pr.merged",
    "signals_recorded": "signal.recorded",
    "patterns_ratified": "pattern.ratified",
    "constraints_delivered": "constraint.delivered",
}
ORDER_DONE = "order.done"


def describe_project(reading: LedgerReading, project: str, since: datetime | None) -> dict:
    records = [
        entry.record
        for entry in reading.entries
        if entry.record.get("project") == project and (since is None or entry.instant >= since)
    ]
    return {
        "view": "project",
        "project": project,
        "since": None if since is None else format_instant(since),
        "orders_done": count_by_name(record["kind"] for record in records if record["event"] == ORDER_DONE),
        **{key: sum(1 for record in records if record["event"] == event) for key, event in COUNTED_EVENTS.items()},
    }
