import argparse
from pathlib import Path

from brigade.command import Argument, Command
from brigade.commands._locate_checkout import locate_checkout
from brigade.commands._locate_recipe_places import locate_recipe_places
from brigade.corpus.read_entity import read_entity
from brigade.ledger.order_done import OrderDone
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.order_started import OrderStarted
from brigade.ledger.read_ledger import read_ledger
from brigade.orders.convert_order import Order, convert_order
from brigade.orders.start_order_run import start_order_run
from brigade.recipes.create_command_performer import create_command_performer
from brigade.recipes.resolve_recipe import resolve_recipe
from brigade.recipes.run_order import DONE, OrderRun, run_order
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runs.create_run_id import create_run_id
from brigade.runs.run_locations import RUNS_DIRECTORY
from brigade.runtime import Runtime

DOCUMENT_SCHEMA_VERSION = 1
ENTITY_TYPE = "ORDER"
PARKED_EXIT_CODE = 1
PARAM_SEPARATOR = "="
PROJECT_VALUE = "project"
NO_PARKED_RUN = None


def _render_text(document: dict) -> str:
    head = f"@ORDER.{document['order']} run {document['run']} {document['state']}"
    if document["state"] == DONE:
        return head
    return f"{head} at {document['step']}: {document['reason']}"


def _decide_exit_code(document: dict) -> int:
    return 0 if document["state"] == DONE else PARKED_EXIT_CODE


def _locate_project(order: Order, runtime: Runtime) -> Path:
    if order.project is None:
        return locate_checkout(runtime)
    return Path(read_project_field(find_project(read_projects(runtime), order.project), "PATH"))


def _find_parked_run(runtime: Runtime, order: Order) -> str | None:
    last_event = None
    for entry in read_ledger(runtime.paths.state_root).entries:
        event = entry.event
        if isinstance(event, OrderStarted | OrderParked | OrderDone) and (event.kind, event.order) == (
            order.recipe,
            order.name,
        ):
            last_event = event
    return last_event.run if isinstance(last_event, OrderParked) else NO_PARKED_RUN


def _start_new_run(runtime: Runtime, order: Order) -> str:
    run_id = create_run_id(runtime.now)
    start_order_run(runtime, order, run_id)
    return run_id


def _read_values(order: Order) -> dict[str, str | None]:
    return {**dict(param.partition(PARAM_SEPARATOR)[::2] for param in order.params), PROJECT_VALUE: order.project}


def order_run(request: argparse.Namespace, runtime: Runtime) -> dict:
    require_operational_corpus(runtime.paths)
    order = convert_order(read_entity(runtime.run_process, runtime.paths.config_root, ENTITY_TYPE, request.name))
    project = _locate_project(order, runtime)
    recipe = resolve_recipe(order.recipe, locate_recipe_places(project, runtime), runtime.run_process).document
    run_id = _find_parked_run(runtime, order) or _start_new_run(runtime, order)
    run = OrderRun(
        order=order.name,
        project=order.project,
        recipe=recipe,
        run_id=run_id,
        run_directory=runtime.paths.state_root / RUNS_DIRECTORY / run_id,
    )
    performers = {"command": create_command_performer(runtime.run_process, project, _read_values(order))}
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, **run_order(runtime, run, performers)}


COMMAND = Command(
    path=("order", "run"),
    help="run an order: the steps of its recipe; resume it at its first undone step where it parked",
    arguments=(Argument(("name",), {"help": "the name of the ORDER entity"}),),
    run=order_run,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
