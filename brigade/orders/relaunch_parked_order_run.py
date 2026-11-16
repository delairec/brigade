import os

from brigade.corpus.read_entity import read_entity
from brigade.ledger.append_event import append_event
from brigade.ledger.order_started import OrderStarted
from brigade.orders.convert_order import convert_order
from brigade.orders.detach_order_run import detach_order_run
from brigade.orders.find_parked_order_run import NO_PARKED_RUN, find_parked_order_run
from brigade.orders.start_order_run import ORDER_RECORD_FILE
from brigade.runs.run_locations import RUNS_DIRECTORY
from brigade.runtime import Runtime

ENTITY_TYPE = "ORDER"


def relaunch_parked_order_run(runtime: Runtime, name: str) -> str | None:
    order = convert_order(read_entity(runtime.run_process, runtime.paths.config_root, ENTITY_TYPE, name))
    run_id = find_parked_order_run(runtime, order)
    if run_id is NO_PARKED_RUN:
        return NO_PARKED_RUN
    instant = runtime.now.timestamp()
    os.utime(runtime.paths.state_root / RUNS_DIRECTORY / run_id / ORDER_RECORD_FILE, (instant, instant))
    append_event(
        runtime.paths, runtime.now, OrderStarted(project=order.project, kind=order.recipe, order=name, run=run_id)
    )
    detach_order_run(runtime, name, run_id)
    return run_id
