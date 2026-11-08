from brigade.corpus.read_entities import Entity
from brigade.registry.read_project_forge import NO_FORGE, read_project_forge


def is_on_a_forge(project: Entity) -> bool:
    return read_project_forge(project) != NO_FORGE
