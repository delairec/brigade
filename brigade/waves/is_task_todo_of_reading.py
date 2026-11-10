from brigade.corpus.read_entities import Entity
from brigade.tasks.read_task_field import read_task_field
from brigade.waves.read_project_tasks import ProjectTasks

STATUS_FIELD = "STATUS"
TODO_STATUS = "todo"
MILESTONE = "MILESTONE"
MILESTONE_PREFIX = "@MILESTONE."
NAMING_NO_MILESTONE = ()


def _name_milestone(milestone: str | None) -> tuple[str, ...]:
    return NAMING_NO_MILESTONE if milestone is None else (MILESTONE_PREFIX + milestone,)


def is_task_todo_of_reading(tasks: ProjectTasks, task: Entity) -> bool:
    return read_task_field(task, STATUS_FIELD) == (TODO_STATUS,) and read_task_field(
        task, MILESTONE
    ) == _name_milestone(tasks.milestone)
