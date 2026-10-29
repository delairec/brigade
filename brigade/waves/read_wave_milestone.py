from collections.abc import Iterable

from brigade.corpus.read_entities import Entity
from brigade.errors import BrigadeError
from brigade.registry.read_project_field import read_project_field

MILESTONE_FIELD = "MILESTONE"
MILESTONE_PREFIX = "@MILESTONE."


def read_wave_milestone(wave: str, tasks: Iterable[Entity]) -> str | None:
    milestones = {read_project_field(task, MILESTONE_FIELD) for task in tasks}
    if len(milestones) > 1:
        raise BrigadeError(f"the tasks of the wave {wave} name more than one milestone")
    milestone = next(iter(milestones), None)
    return None if milestone is None else milestone.removeprefix(MILESTONE_PREFIX)
