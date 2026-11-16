from pathlib import Path

from brigade.recipes.locate_recipes import locate_recipes
from brigade.recipes.recipe_places import RecipePlaces
from brigade.registry.find_project_at import find_project_at
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime


def locate_recipe_places(runtime: Runtime) -> RecipePlaces:
    project = Path.cwd()
    return locate_recipes(project, find_project_at(read_projects(runtime), project), runtime.paths)
