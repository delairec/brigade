import argparse
import dataclasses
from collections.abc import Callable, Mapping
from datetime import date
from pathlib import Path

from brigade.collecting.collect_document import Collection, CollectionRequest, collect_document
from brigade.collecting.collector_environment import CollectorInputs
from brigade.command import Argument, Command
from brigade.commands._equip_collector import equip_collector
from brigade.commands._equip_preflight import equip_preflight
from brigade.commands._equip_study import equip_study
from brigade.commands._locate_checkout import locate_checkout
from brigade.commands._locate_preflights import locate_preflights
from brigade.commands._locate_recipe_places import locate_recipe_places
from brigade.commands.run import run as launch_run
from brigade.corpus.read_entities import Entity
from brigade.corpus.read_entity import read_entity
from brigade.ledger.order_done import OrderDone
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.order_started import OrderStarted
from brigade.ledger.read_ledger import read_ledger
from brigade.orders.convert_order import Order, convert_order
from brigade.orders.start_order_run import start_order_run
from brigade.preflights.run_preflight import PreflightOutcome, PreflightRun, run_preflight
from brigade.recipes.create_collect_performer import create_collect_performer
from brigade.recipes.create_command_performer import create_command_performer
from brigade.recipes.create_gate_performer import create_gate_performer
from brigade.recipes.create_judge_performer import create_judge_performer
from brigade.recipes.create_output_performer import create_output_performer
from brigade.recipes.hand_result import ResultHandoff, hand_result
from brigade.recipes.keep_result import keep_result
from brigade.recipes.resolve_recipe import resolve_recipe
from brigade.recipes.run_order import DONE, OrderRun, StepPerformer, run_order
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runs.create_run_id import create_run_id
from brigade.runs.run_locations import RUNS_DIRECTORY
from brigade.runtime import Runtime
from brigade.system.collector_places import locate_collectors

DOCUMENT_SCHEMA_VERSION = 1
ENTITY_TYPE = "ORDER"
PARKED_EXIT_CODE = 1
PARAM_SEPARATOR = "="
PROJECT_VALUE = "project"
NO_PARKED_RUN = None
NO_PROJECT = None
NO_GATE_PARAMETERS = {}
COLLECTOR_KIND = "collector"
BEGINNING = date(1970, 1, 1)


def _render_text(document: dict) -> str:
    head = f"@ORDER.{document['order']} run {document['run']} {document['state']}"
    if document["state"] == DONE:
        return head
    return f"{head} at {document['step']}: {document['reason']}"


def _decide_exit_code(document: dict) -> int:
    return 0 if document["state"] == DONE else PARKED_EXIT_CODE


def _find_order_project(order: Order, runtime: Runtime) -> Entity | None:
    if order.project is None:
        return NO_PROJECT
    return find_project(read_projects(runtime), order.project)


def _locate_project(project: Entity | None, runtime: Runtime) -> Path:
    if project is None:
        return locate_checkout(runtime)
    return Path(read_project_field(project, "PATH"))


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


def _run_gate(name: str, project: Path, runtime: Runtime) -> PreflightOutcome:
    run = PreflightRun(
        name=name,
        project=project,
        parameters=NO_GATE_PARAMETERS,
        equipment=equip_collector(project, runtime),
        preflights=locate_preflights(project, runtime),
        plugins=equip_preflight(runtime),
    )
    return run_preflight(run, runtime)


def _equip_collect(project: Path, runtime: Runtime) -> Callable[[str, Mapping[str, str], Path], Collection]:
    def collect(name: str, parameters: Mapping[str, str], place: Path) -> Collection:
        collector = runtime.resolve_plugin(COLLECTOR_KIND, name, places=locate_collectors(project, runtime.paths))
        request = CollectionRequest(
            inputs=CollectorInputs(project=project, since=BEGINNING, parameters=dict(parameters)),
            refresh=False,
            equipment=equip_collector(project, runtime),
        )
        place_paths = dataclasses.replace(runtime.paths, run_directory=place)
        return collect_document(collector, request, dataclasses.replace(runtime, paths=place_paths))

    return collect


def _equip_output(order: Order, project: Entity | None, run_id: str, runtime: Runtime) -> StepPerformer:
    def hand(output: str, answer: Path) -> dict:
        handoff = ResultHandoff(
            runtime=runtime,
            order=order.name,
            project=order.project,
            output=output,
            run_id=run_id,
            run_directory=answer.parent,
            equipment=equip_study(project, runtime),
        )
        return hand_result(handoff)

    return create_output_performer(lambda result: keep_result(runtime, order.name, result), hand, order.output)


def order_run(request: argparse.Namespace, runtime: Runtime) -> dict:
    require_operational_corpus(runtime.paths)
    order = convert_order(read_entity(runtime.run_process, runtime.paths.config_root, ENTITY_TYPE, request.name))
    project_entity = _find_order_project(order, runtime)
    project = _locate_project(project_entity, runtime)
    recipe = resolve_recipe(order.recipe, locate_recipe_places(project, runtime), runtime.run_process).document
    run_id = _find_parked_run(runtime, order) or _start_new_run(runtime, order)
    run = OrderRun(
        order=order.name,
        project=order.project,
        recipe=recipe,
        run_id=run_id,
        run_directory=runtime.paths.state_root / RUNS_DIRECTORY / run_id,
    )
    values = _read_values(order)
    performers = {
        "collect": create_collect_performer(_equip_collect(project, runtime), values),
        "command": create_command_performer(runtime.run_process, project, values),
        "gate": create_gate_performer(lambda name: _run_gate(name, project, runtime)),
        "judge": create_judge_performer(lambda request: launch_run(request, runtime)),
        "output": _equip_output(order, project_entity, run_id, runtime),
    }
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, **run_order(runtime, run, performers)}


COMMAND = Command(
    path=("order", "run"),
    help="run an order: the steps of its recipe; resume it at its first undone step where it parked",
    arguments=(Argument(("name",), {"help": "the name of the ORDER entity"}),),
    run=order_run,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
