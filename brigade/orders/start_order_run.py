from brigade.ledger.append_event import append_event
from brigade.ledger.order_started import OrderStarted
from brigade.orders.convert_order import Order
from brigade.runs.run_locations import RUNS_DIRECTORY
from brigade.runtime import Runtime
from brigade.system.write_json_atomically import write_json_atomically

ORDER_RECORD_FILE = "order.json"
ORDER_RECORD_SCHEMA_VERSION = 1


def start_order_run(runtime: Runtime, order: Order, run_id: str) -> None:
    write_json_atomically(
        runtime.paths.state_root / RUNS_DIRECTORY / run_id / ORDER_RECORD_FILE,
        {"schema_version": ORDER_RECORD_SCHEMA_VERSION, "order": order.to_document()},
    )
    append_event(
        runtime.paths, runtime.now, OrderStarted(project=order.project, kind=order.recipe, order=order.name, run=run_id)
    )
