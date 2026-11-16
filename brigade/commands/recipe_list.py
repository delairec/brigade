import argparse

from brigade.command import Command
from brigade.commands._locate_recipe_places import locate_recipe_places
from brigade.recipes.list_recipes import list_recipes
from brigade.runtime import Runtime
from brigade.system.render_table import render_table

DOCUMENT_SCHEMA_VERSION = 1
HEADER = ("name", "source")
NATIVE_RECIPES = ({"name": "wave", "source": "native"},)


def _render_text(document: dict) -> str:
    return render_table(HEADER, [(recipe["name"], recipe["source"]) for recipe in document["recipes"]])


def recipe_list(request: argparse.Namespace, runtime: Runtime) -> dict:
    recipes = list_recipes(locate_recipe_places(runtime), runtime.run_process)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "recipes": [*({"name": recipe.name, "source": recipe.source} for recipe in recipes), *NATIVE_RECIPES],
    }


COMMAND = Command(
    path=("recipe", "list"),
    help="list every recipe found, its name and its source, in the order they resolve",
    group_help="list, show and lint the recipes",
    run=recipe_list,
    render_text=_render_text,
)
