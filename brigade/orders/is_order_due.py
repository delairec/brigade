from dataclasses import dataclass
from datetime import datetime

from brigade.errors import BrigadeError
from brigade.studies.read_schedule import read_schedule

ACTIVE_STATUS = "active"


@dataclass(frozen=True)
class OrderFacts:
    name: str
    every: str | None
    status: str
    last_started: datetime | None
    parked: bool


def is_order_due(order: OrderFacts, now: datetime) -> bool:
    if order.status != ACTIVE_STATUS or order.every is None or order.parked:
        return False
    try:
        schedule = read_schedule(order.every)
    except BrigadeError as refusal:
        raise BrigadeError(f"@ORDER.{order.name}: {refusal}") from None
    return order.last_started is None or schedule.has_passed_since(order.last_started, now)
