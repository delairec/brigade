import argparse
import json

from brigade.command import Argument, Command
from brigade.commands._locate_recipe_places import locate_recipe_places
from brigade.recipes.resolve_recipe import resolve_recipe
from brigade.runtime import Runtime

DOCUMENT_SCHEMA_VERSION = 1
INDENT = 2


def _render_text(document: dict) -> str:
    return f"source {document['source']}\n{json.dumps(document['recipe'], indent=INDENT)}"


def recipe_show(request: argparse.Namespace, runtime: Runtime) -> dict:
    recipe = resolve_recipe(request.name, locate_recipe_places(runtime), runtime.run_process)
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "source": recipe.source, "recipe": recipe.document}


COMMAND = Command(
    path=("recipe", "show"),
    help="print the recipe named, as it resolves, and its source",
    arguments=(Argument(("name",), {"help": "the name of the recipe"}),),
    run=recipe_show,
    render_text=_render_text,
)
