from collections.abc import Callable

from brigade.recipes.list_project_recipes import list_project_recipes
from brigade.recipes.recipe_places import RecipePlaces
from brigade.system.run_process import ProcessRecord, ProcessRequest


def read_project_commands(
    places: RecipePlaces, recipe: str, run_process: Callable[[ProcessRequest], ProcessRecord]
) -> tuple[tuple[str, ...], ...]:
    found = next((found for found in list_project_recipes(places, run_process) if found.name == recipe), None)
    if found is None:
        return ()
    return tuple(tuple(step["argv"]) for step in found.document["steps"])
