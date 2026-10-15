from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.registry.read_project_field import read_project_field

PATH_FIELD = "PATH"


def find_project_at(projects: tuple[Entity, ...], path: Path) -> Entity | None:
    return next((project for project in projects if read_project_field(project, PATH_FIELD) == str(path)), None)
