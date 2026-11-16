from brigade.ledger.order_done import OrderDone
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.order_started import OrderStarted
from brigade.ledger.read_ledger import read_ledger
from brigade.orders.convert_order import Order
from brigade.runtime import Runtime

NO_PARKED_RUN = None


def find_parked_order_run(runtime: Runtime, order: Order) -> str | None:
    last_event = None
    for entry in read_ledger(runtime.paths.state_root).entries:
        event = entry.event
        if isinstance(event, OrderStarted | OrderParked | OrderDone) and (event.kind, event.order) == (
            order.recipe,
            order.name,
        ):
            last_event = event
    return last_event.run if isinstance(last_event, OrderParked) else NO_PARKED_RUN
