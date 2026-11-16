import argparse

from brigade.command import Command
from brigade.corpus.read_entities import read_entities
from brigade.orders.convert_order import convert_order
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime
from brigade.system.render_table import render_table

DOCUMENT_SCHEMA_VERSION = 1
ENTITY_TYPE = "ORDER"
NO_ORDER = "no order recorded"
NO_VALUE = "-"
COLUMNS = ("name", "recipe", "project", "every", "status")


def _present(value: str | None) -> str:
    return NO_VALUE if value is None else value


def _render_text(document: dict) -> str:
    orders = document["orders"]
    if not orders:
        return NO_ORDER
    return render_table(COLUMNS, [tuple(_present(order[column]) for column in COLUMNS) for order in orders])


def order_list(request: argparse.Namespace, runtime: Runtime) -> dict:
    require_operational_corpus(runtime.paths)
    orders = (
        convert_order(entity) for entity in read_entities(runtime.run_process, runtime.paths.config_root, ENTITY_TYPE)
    )
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "orders": [{column: order.to_document()[column] for column in COLUMNS} for order in orders],
    }


COMMAND = Command(
    path=("order", "list"),
    help="list every order with its recipe, its project, its schedule and its status",
    run=order_list,
    render_text=_render_text,
)
