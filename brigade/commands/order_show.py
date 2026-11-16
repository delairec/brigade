import argparse

from brigade.command import Argument, Command
from brigade.corpus.read_entity import read_entity
from brigade.ledger.format_instant import format_instant
from brigade.ledger.order_done import OrderDone
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.order_started import OrderStarted
from brigade.ledger.read_ledger import read_ledger
from brigade.orders.convert_order import convert_order
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime
from brigade.system.render_table import render_table

DOCUMENT_SCHEMA_VERSION = 1
ENTITY_TYPE = "ORDER"
RUNNING = "running"
OUTCOMES = {OrderDone: "done", OrderParked: "parked"}
RUN_COLUMNS = ("run", "started", "outcome")
ON_DEMAND = "on demand"
MACHINE_WIDE = "machine-wide"


def _render_text(document: dict) -> str:
    order = document["order"]
    project = MACHINE_WIDE if order["project"] is None else f"project {order['project']}"
    every = ON_DEMAND if order["every"] is None else f"every {order['every']}"
    head = f"@ORDER.{order['name']}: recipe {order['recipe']}, {project}, {every}, {order['status']}"
    runs = [tuple(run[column] for column in RUN_COLUMNS) for run in document["runs"]]
    return f"{head}\n{render_table(RUN_COLUMNS, runs)}"


def _read_runs(runtime: Runtime, name: str) -> list[dict]:
    runs: dict[str, dict] = {}
    for entry in read_ledger(runtime.paths.state_root).entries:
        event = entry.event
        if isinstance(event, OrderStarted) and event.order == name:
            runs[event.run] = {"run": event.run, "started": format_instant(entry.instant), "outcome": RUNNING}
        elif isinstance(event, OrderDone | OrderParked) and event.run in runs:
            runs[event.run]["outcome"] = OUTCOMES[type(event)]
    return list(runs.values())


def order_show(request: argparse.Namespace, runtime: Runtime) -> dict:
    require_operational_corpus(runtime.paths)
    order = convert_order(read_entity(runtime.run_process, runtime.paths.config_root, ENTITY_TYPE, request.name))
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "order": order.to_document(),
        "runs": _read_runs(runtime, request.name),
    }


COMMAND = Command(
    path=("order", "show"),
    help="print one order with its runs",
    arguments=(Argument(("name",), {"help": "the name of the ORDER entity"}),),
    run=order_show,
    render_text=_render_text,
)
