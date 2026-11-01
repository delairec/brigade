from dataclasses import dataclass
from datetime import datetime

from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.order_done import OrderDone
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.order_started import OrderStarted
from brigade.studies.study_run_context import STUDY_KIND

OUTCOMES = {OrderStarted: "started", OrderDone: "done", OrderParked: "parked"}
NEVER_STARTED = None


@dataclass(frozen=True)
class LastStudyOrder:
    run: str
    outcome: str
    started: datetime | None


def read_last_study_orders(entries: tuple[LedgerEntry, ...]) -> dict[str, LastStudyOrder]:
    last_orders = {}
    for entry in entries:
        event = entry.event
        if type(event) not in OUTCOMES or event.kind != STUDY_KIND:
            continue
        earlier = last_orders.get(event.order)
        started = entry.instant if isinstance(event, OrderStarted) else getattr(earlier, "started", NEVER_STARTED)
        last_orders[event.order] = LastStudyOrder(run=event.run, outcome=OUTCOMES[type(event)], started=started)
    return last_orders
