from brigade.corpus.read_entities import Entity
from brigade.registry.describe_remote import NO_FORGE
from brigade.registry.read_project_field import read_project_field

FORGE_COLLECTORS = ("pr-list",)
FORGE_FIELD = "FORGE"
FORGE_ABSENCE = f"FORGE {NO_FORGE}"


def find_absence(name: str, project: Entity | None) -> str | None:
    if name in FORGE_COLLECTORS and read_project_field(project, FORGE_FIELD) == NO_FORGE:
        return FORGE_ABSENCE
    return None
