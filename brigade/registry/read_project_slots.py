from brigade.corpus.read_entities import Entity
from brigade.registry.read_project_field import read_project_field

SLOTS_FIELD = "SLOTS"
PROJECT_SLOTS = 4


def read_project_slots(project: Entity) -> int:
    slots = read_project_field(project, SLOTS_FIELD)
    return PROJECT_SLOTS if slots is None else int(slots)
