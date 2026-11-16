from collections.abc import Callable

from brigade.errors import BrigadeError
from brigade.recipes.list_recipes import list_recipes
from brigade.recipes.recipe_found import RecipeFound
from brigade.recipes.recipe_places import RecipePlaces
from brigade.system.run_process import ProcessRecord, ProcessRequest


def resolve_recipe(
    name: str, places: RecipePlaces, run_process: Callable[[ProcessRequest], ProcessRecord]
) -> RecipeFound:
    found = next((recipe for recipe in list_recipes(places, run_process) if recipe.name == name), None)
    if found is None:
        raise BrigadeError(f"no recipe {name}: not in the project, in {places.machine_directory} or built in")
    return found
