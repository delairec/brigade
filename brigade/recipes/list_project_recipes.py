from collections.abc import Callable
from pathlib import Path

from brigade.corpus.read_awawa_document import read_awawa_document
from brigade.recipes.convert_recipe_entity import convert_recipe_entity
from brigade.recipes.read_recipe_files import read_recipe_files
from brigade.recipes.recipe_found import RecipeFound
from brigade.recipes.recipe_places import RecipePlaces
from brigade.system.collector_places import PROJECT_SOURCE
from brigade.system.run_process import ProcessRecord, ProcessRequest

RECIPE_TYPE = "RECIPE"


def _read_entities(corpus: Path, run_process: Callable[[ProcessRequest], ProcessRecord]) -> list[RecipeFound]:
    status = read_awawa_document(run_process, corpus, ("status",))
    return [
        RecipeFound(
            name=entity["name"],
            source=PROJECT_SOURCE,
            document=convert_recipe_entity(
                read_awawa_document(run_process, corpus, ("show", f"@{RECIPE_TYPE}.{entity['name']}"))
            ),
        )
        for entity in status["entities"]
        if entity["type"] == RECIPE_TYPE
    ]


def list_project_recipes(
    places: RecipePlaces, run_process: Callable[[ProcessRequest], ProcessRecord]
) -> tuple[RecipeFound, ...]:
    if places.project_corpus is None:
        return tuple(read_recipe_files(places.project_directory, PROJECT_SOURCE))
    return tuple(_read_entities(places.project_corpus, run_process))
