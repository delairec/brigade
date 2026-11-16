import argparse
from dataclasses import dataclass
from pathlib import Path

from brigade.command import Argument, Command
from brigade.commands._locate_checkout import locate_checkout
from brigade.commands._locate_recipe_places import locate_recipe_places
from brigade.commands.order_run import order_run
from brigade.errors import BrigadeError
from brigade.orders.record_order import NewOrder, record_order
from brigade.recipes.resolve_recipe import resolve_recipe
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime
from brigade.studies.read_schedule import read_schedule
from brigade.system.instant_formats import COMPACT_INSTANT_FORMAT

DOCUMENT_SCHEMA_VERSION = 1
PARAM_SEPARATOR = "="
NO_TEXT = None


@dataclass(frozen=True)
class OrderWords:
    params: tuple[str, ...]
    text: str | None


def _render_text(document: dict) -> str:
    if document["every"] is None:
        return f"@ORDER.{document['order']} recorded, run {document['run']} {document['state']}"
    return f"@ORDER.{document['order']} recorded, every {document['every']}"


def _locate_project(request: argparse.Namespace, runtime: Runtime) -> Path:
    if request.project is None:
        return locate_checkout(runtime)
    return Path(read_project_field(find_project(read_projects(runtime), request.project), "PATH"))


def _sort_words(words: list[str], recipe: dict) -> OrderWords:
    params = tuple(word for word in words if word.partition(PARAM_SEPARATOR)[0] in recipe["params"])
    texts = [word for word in words if word not in params]
    if len(texts) > 1:
        raise BrigadeError(
            f"an order takes one text, and the words {' and '.join(texts)} are {len(texts)}: "
            f"quote the text, or write key=value for a param of the recipe {recipe['name']}"
        )
    return OrderWords(params=params, text=next(iter(texts), NO_TEXT))


def order_new(request: argparse.Namespace, runtime: Runtime) -> dict:
    require_operational_corpus(runtime.paths)
    project = _locate_project(request, runtime)
    recipe = resolve_recipe(request.recipe, locate_recipe_places(project, runtime), runtime.run_process).document
    words = _sort_words(request.words, recipe)
    if request.every is not None:
        read_schedule(request.every)
    name = f"{recipe['name'].replace('-', '_')}_{runtime.now.strftime(COMPACT_INSTANT_FORMAT)}"
    record_order(
        runtime,
        NewOrder(
            name=name,
            recipe=recipe["name"],
            project=request.project,
            text=words.text,
            params=words.params,
            every=request.every,
        ),
    )
    document = {"schema_version": DOCUMENT_SCHEMA_VERSION, "order": name, "every": request.every}
    if request.every is not None:
        return document
    ran = order_run(argparse.Namespace(name=name), runtime)
    return {**document, "run": ran["run"], "state": ran["state"]}


COMMAND = Command(
    path=("order", "new"),
    help="record an order of a recipe and run it once unless it has a schedule",
    group_help="record the orders of the recipes, run them and change their status",
    arguments=(
        Argument(("recipe",), {"help": "the name of the recipe"}),
        Argument(("--project",), {"help": "the registered project; absent for a machine-wide order"}),
        Argument(("--every",), {"help": "a schedule of the tick; absent, the order runs once"}),
        Argument(("words",), {"nargs": "*", "help": "key=value for a param of the recipe, else the text"}),
    ),
    run=order_new,
    render_text=_render_text,
)
