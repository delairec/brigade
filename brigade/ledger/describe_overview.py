from brigade.ledger.count_by_name import count_by_name
from brigade.ledger.format_instant import format_instant
from brigade.ledger.group_runs import group_runs
from brigade.ledger.read_ledger import LedgerReading
from brigade.ledger.run_finished import RunFinished


def _count_outcomes(finished: list[RunFinished]) -> dict:
    return {
        "outcomes": count_by_name(segment.outcome for segment in finished),
        "error_classes": count_by_name(segment.error_class for segment in finished if segment.error_class is not None),
    }


def describe_overview(reading: LedgerReading) -> dict:
    events = [entry.event for entry in reading.entries]
    instants = [entry.instant for entry in reading.entries]
    runs = group_runs(reading.entries)
    return {
        "view": "overview",
        "events": count_by_name(event.name for event in events),
        "first": format_instant(min(instants)) if instants else None,
        "last": format_instant(max(instants)) if instants else None,
        "files": list(reading.files),
        "runs": _count_outcomes([run.last for run in runs]),
        "segments": _count_outcomes([segment for run in runs for segment in run.segments]),
    }
