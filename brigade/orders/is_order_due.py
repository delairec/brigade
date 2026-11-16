from dataclasses import dataclass
from datetime import datetime

from brigade.errors import BrigadeError
from brigade.ledger.format_instant import format_instant
from brigade.studies.read_schedule import read_schedule

ACTIVE_STATUS = "active"


@dataclass(frozen=True)
class OrderFacts:
    name: str
    every: str | None
    status: str
    last_started: datetime | None
    parked: bool

    def to_document(self) -> dict:
        return {
            "order": self.name,
            "every": self.every,
            "status": self.status,
            "last_started": None if self.last_started is None else format_instant(self.last_started),
            "parked": self.parked,
        }


def is_order_due(order: OrderFacts, now: datetime) -> bool:
    if order.status != ACTIVE_STATUS or order.every is None or order.parked:
        return False
    try:
        schedule = read_schedule(order.every)
    except BrigadeError as refusal:
        raise BrigadeError(f"@ORDER.{order.name}: {refusal}") from None
    return order.last_started is None or schedule.has_passed_since(order.last_started, now)
