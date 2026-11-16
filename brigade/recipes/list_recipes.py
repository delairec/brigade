import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from importlib.resources.abc import Traversable
from pathlib import Path

from brigade.corpus.read_awawa_document import read_awawa_document
from brigade.recipes.convert_recipe_entity import convert_recipe_entity
from brigade.recipes.recipe_places import RecipePlaces
from brigade.system.collector_places import BUILT_IN_SOURCE, MACHINE_SOURCE, PROJECT_SOURCE
from brigade.system.run_process import ProcessRecord, ProcessRequest

RECIPE_SUFFIX = ".toml"
RECIPE_TYPE = "RECIPE"


@dataclass(frozen=True)
class RecipeFound:
    name: str
    source: str
    document: dict


def _read_files(directory: Traversable, source: str) -> list[RecipeFound]:
    if not directory.is_dir():
        return []
    return [
        RecipeFound(
            name=entry.name.removesuffix(RECIPE_SUFFIX),
            source=source,
            document=tomllib.loads(entry.read_text(encoding="utf-8")),
        )
        for entry in sorted(directory.iterdir(), key=lambda entry: entry.name)
        if entry.name.endswith(RECIPE_SUFFIX)
    ]


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


def list_recipes(
    places: RecipePlaces, run_process: Callable[[ProcessRequest], ProcessRecord]
) -> tuple[RecipeFound, ...]:
    project = (
        _read_files(places.project_directory, PROJECT_SOURCE)
        if places.project_corpus is None
        else _read_entities(places.project_corpus, run_process)
    )
    return (
        *project,
        *_read_files(places.machine_directory, MACHINE_SOURCE),
        *_read_files(places.built_ins, BUILT_IN_SOURCE),
    )
