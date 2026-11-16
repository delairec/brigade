from datetime import datetime

from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.order_done import OrderDone
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.order_started import OrderStarted
from brigade.orders.convert_order import Order
from brigade.orders.is_order_due import OrderFacts

ORDER_EVENTS = (OrderStarted, OrderParked, OrderDone)


def _describe_order_facts(order: Order, entries: tuple[LedgerEntry, ...]) -> OrderFacts:
    last_started: datetime | None = None
    parked = False
    for entry in entries:
        event = entry.event
        if not isinstance(event, ORDER_EVENTS) or (event.kind, event.order) != (order.recipe, order.name):
            continue
        if isinstance(event, OrderStarted):
            last_started = entry.instant
        parked = isinstance(event, OrderParked)
    return OrderFacts(name=order.name, every=order.every, status=order.status, last_started=last_started, parked=parked)


def read_order_facts(orders: tuple[Order, ...], entries: tuple[LedgerEntry, ...]) -> tuple[OrderFacts, ...]:
    return tuple(_describe_order_facts(order, entries) for order in orders)
