from brigade.ledger.constraint_delivered import ConstraintDelivered
from brigade.ledger.count_by_name import count_by_name
from brigade.ledger.order_done import OrderDone
from brigade.ledger.pattern_ratified import PatternRatified
from brigade.ledger.pr_merged import PrMerged
from brigade.ledger.read_ledger import LedgerReading
from brigade.ledger.signal_recorded import SignalRecorded
from brigade.ledger.wave_started import WaveStarted

COUNTED_EVENTS = {
    "waves_started": WaveStarted,
    "pull_requests_merged": PrMerged,
    "signals_recorded": SignalRecorded,
    "patterns_ratified": PatternRatified,
    "constraints_delivered": ConstraintDelivered,
}


def describe_project(reading: LedgerReading, project: str) -> dict:
    events = [entry.event for entry in reading.entries if getattr(entry.event, "project", None) == project]
    return {
        "view": "project",
        "project": project,
        "orders_done": count_by_name(event.kind for event in events if isinstance(event, OrderDone)),
        **{key: sum(1 for event in events if isinstance(event, kind)) for key, kind in COUNTED_EVENTS.items()},
    }
