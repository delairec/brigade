from brigade.corpus.read_entities import Entity
from brigade.errors import TaskTypeMissing
from brigade.registry.read_project_field import read_project_field
from brigade.tick.name_task_branch import name_task_branch

TYPE_FIELD = "TYPE"
TITLE_FIELD = "TITLE"


def name_branch_of_task(task: Entity) -> str:
    task_type = read_project_field(task, TYPE_FIELD)
    if task_type is None:
        raise TaskTypeMissing(f"@TASK.{task.name} carries no TYPE to name its branch")
    return name_task_branch(task_type, task.name, read_project_field(task, TITLE_FIELD))
