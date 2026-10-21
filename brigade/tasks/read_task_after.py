from brigade.corpus.read_entities import Entity
from brigade.tasks.read_task_field import read_task_field

AFTER_FIELD = "AFTER"
TASK_REFERENCE_PREFIX = "@TASK."


def read_task_after(task: Entity) -> tuple[str, ...]:
    return tuple(after.removeprefix(TASK_REFERENCE_PREFIX) for after in read_task_field(task, AFTER_FIELD))
