from brigade.corpus.read_entities import Entity
from brigade.registry.read_project_field import read_project_field

NO_FORGE = "none"


def read_project_forge(project: Entity) -> str:
    return read_project_field(project, "FORGE") or NO_FORGE
