from collections.abc import Callable

from brigade.recipes.list_project_recipes import list_project_recipes
from brigade.recipes.read_recipe_files import read_recipe_files
from brigade.recipes.recipe_found import RecipeFound
from brigade.recipes.recipe_places import RecipePlaces
from brigade.system.collector_places import BUILT_IN_SOURCE, MACHINE_SOURCE
from brigade.system.run_process import ProcessRecord, ProcessRequest


def list_recipes(
    places: RecipePlaces, run_process: Callable[[ProcessRequest], ProcessRecord]
) -> tuple[RecipeFound, ...]:
    return (
        *list_project_recipes(places, run_process),
        *read_recipe_files(places.machine_directory, MACHINE_SOURCE),
        *read_recipe_files(places.built_ins, BUILT_IN_SOURCE),
    )
