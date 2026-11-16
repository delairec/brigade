from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.recipes.recipe_places import (
    BUILT_IN_RECIPES,
    MACHINE_RECIPES_DIRECTORY,
    PROJECT_RECIPES_DIRECTORY,
    RecipePlaces,
)
from brigade.registry.read_corpus_workspace import MODE_FIELD, NONE_MODE, read_corpus_workspace
from brigade.registry.read_project_field import read_project_field
from brigade.system.paths import Paths


def _locate_corpus(project: Path, entity: Entity | None) -> Path | None:
    if entity is None or read_project_field(entity, MODE_FIELD) == NONE_MODE:
        return None
    return project / read_corpus_workspace(entity)


def locate_recipes(project: Path, entity: Entity | None, paths: Paths) -> RecipePlaces:
    return RecipePlaces(
        project_corpus=_locate_corpus(project, entity),
        project_directory=project / PROJECT_RECIPES_DIRECTORY,
        machine_directory=paths.config_root / MACHINE_RECIPES_DIRECTORY,
        built_ins=BUILT_IN_RECIPES,
    )
