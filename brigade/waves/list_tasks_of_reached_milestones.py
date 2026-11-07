from collections.abc import Callable
from dataclasses import dataclass

from brigade.corpus.read_awawa_document import read_awawa_document
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.tasks.read_task_field import read_task_field
from brigade.waves.read_project_tasks import ProjectTasks

MILESTONE = "MILESTONE"
MILESTONE_PREFIX = "@MILESTONE."
STATUS_FIELD = "STATUS"
REACHED_STATUS = "reached"
OPEN_STATUSES = frozenset({("draft",), ("todo",)})
NO_TASK_OF_A_REACHED_MILESTONE = ()


@dataclass(frozen=True)
class TaskOfAReachedMilestone:
    task: str
    milestone: str


def list_tasks_of_reached_milestones(
    run_process: Callable[[ProcessRequest], ProcessRecord], tasks: ProjectTasks
) -> tuple[TaskOfAReachedMilestone, ...]:
    open_tasks = tuple(
        TaskOfAReachedMilestone(task=task.name, milestone=read_task_field(task, MILESTONE)[0])
        for task in tasks.by_name.values()
        if read_task_field(task, STATUS_FIELD) in OPEN_STATUSES and read_task_field(task, MILESTONE)
    )
    if not open_tasks:
        return NO_TASK_OF_A_REACHED_MILESTONE
    status = read_awawa_document(
        run_process, tasks.root, ("status", MILESTONE, "--where", f"{STATUS_FIELD}=={REACHED_STATUS}")
    )
    reached = frozenset(MILESTONE_PREFIX + entity["name"] for entity in status["entities"])
    return tuple(task for task in open_tasks if task.milestone in reached)
