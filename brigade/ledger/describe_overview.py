from brigade.ledger.count_by_name import count_by_name
from brigade.ledger.format_instant import format_instant
from brigade.ledger.read_ledger import LedgerReading
from brigade.ledger.run_finished import RunFinished


def describe_overview(reading: LedgerReading) -> dict:
    events = [entry.event for entry in reading.entries]
    instants = [entry.instant for entry in reading.entries]
    runs = [event for event in events if isinstance(event, RunFinished)]
    return {
        "view": "overview",
        "events": count_by_name(event.name for event in events),
        "first": format_instant(min(instants)) if instants else None,
        "last": format_instant(max(instants)) if instants else None,
        "files": list(reading.files),
        "runs": {
            "outcomes": count_by_name(run.outcome for run in runs),
            "error_classes": count_by_name(run.error_class for run in runs if run.error_class is not None),
        },
    }
