from brigade.corpus.read_entities import Entity
from brigade.registry.read_project_field import read_project_field

GITHUB_FORGE = "github"


def is_on_github(project: Entity) -> bool:
    return read_project_field(project, "FORGE") == GITHUB_FORGE
