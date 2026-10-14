from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.errors import BrigadeError
from brigade.registry.find_project_at import find_project_at


def require_project_at(projects: tuple[Entity, ...], path: Path) -> Entity:
    project = find_project_at(projects, path)
    if project is None:
        raise BrigadeError(f"no registered project at {path}")
    return project
