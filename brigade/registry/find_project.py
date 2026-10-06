from brigade.corpus.read_entities import Entity
from brigade.errors import BrigadeError


def find_project(projects: tuple[Entity, ...], name: str) -> Entity:
    for project in projects:
        if project.name == name:
            return project
    raise BrigadeError(f"@PROJECT.{name} is not registered")
