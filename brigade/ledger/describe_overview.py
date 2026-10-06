from brigade.ledger.count_by_name import count_by_name
from brigade.ledger.declared_events import RUN_FINISHED
from brigade.ledger.format_instant import format_instant
from brigade.ledger.read_ledger import LedgerReading


def describe_overview(reading: LedgerReading) -> dict:
    records = [entry.record for entry in reading.entries]
    instants = [entry.instant for entry in reading.entries]
    runs = [record for record in records if record["event"] == RUN_FINISHED]
    return {
        "view": "overview",
        "events": count_by_name(record["event"] for record in records),
        "first": format_instant(min(instants)) if instants else None,
        "last": format_instant(max(instants)) if instants else None,
        "files": list(reading.files),
        "runs": {
            "outcomes": count_by_name(run["outcome"] for run in runs),
            "error_classes": count_by_name(run["error_class"] for run in runs if run["error_class"] is not None),
        },
    }
