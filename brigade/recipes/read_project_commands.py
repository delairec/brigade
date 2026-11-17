from collections.abc import Callable

from brigade.recipes.lint_recipe import STEP_SHAPES
from brigade.recipes.list_project_recipes import list_project_recipes
from brigade.recipes.recipe_places import RecipePlaces
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.system.validate_document import DocumentInvalid, Field, validate_document

COMMAND_KIND = "command"
COMMAND_STEP = Field(
    kinds=(dict,), fields={"kind": Field(kinds=(str,), values=(COMMAND_KIND,)), **STEP_SHAPES[COMMAND_KIND]}
)
PROJECT_RECIPE_SHAPE = {"steps": Field(kinds=(list,), items=COMMAND_STEP)}


def read_project_commands(
    places: RecipePlaces, recipe: str, run_process: Callable[[ProcessRequest], ProcessRecord]
) -> tuple[tuple[str, ...], ...]:
    found = next((found for found in list_project_recipes(places, run_process) if found.name == recipe), None)
    if found is None:
        return ()
    try:
        validate_document(found.document, PROJECT_RECIPE_SHAPE)
    except DocumentInvalid as invalid:
        raise DocumentInvalid(f"the recipe {recipe} of the project: {invalid}") from None
    return tuple(tuple(step["argv"]) for step in found.document["steps"])
