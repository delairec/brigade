from collections.abc import Callable
from dataclasses import dataclass

from brigade.corpus.read_awawa_document import read_awawa_document
from brigade.corpus.read_entity import Entity, read_entity
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.tasks.read_task_field import read_task_field
from brigade.waves.read_project_tasks import ProjectTasks

MILESTONE = "MILESTONE"
MILESTONE_PREFIX = "@MILESTONE."
STATUS_FIELD = "STATUS"
AFTER_FIELD = "AFTER"
ACTIVE_STATUS = "active"
REACHED_STATUS = "reached"


@dataclass(frozen=True)
class WaitingMilestone:
    milestone: str
    after: tuple[str, ...]


@dataclass(frozen=True)
class ServedMilestones:
    served: tuple[str, ...]
    waiting: tuple[WaitingMilestone, ...]


NO_MILESTONE_SERVED = ServedMilestones(served=(), waiting=())


def _list_milestones(
    run_process: Callable[[ProcessRequest], ProcessRecord], main: ProjectTasks, status: str
) -> tuple[str, ...]:
    document = read_awawa_document(
        run_process, main.root, ("status", MILESTONE, "--where", f"{STATUS_FIELD}=={status}")
    )
    return tuple(entity["name"] for entity in document["entities"])


def _list_after_not_reached(milestone: Entity, reached: frozenset[str]) -> tuple[str, ...]:
    return tuple(after for after in read_task_field(milestone, AFTER_FIELD) if after not in reached)


def read_served_milestones(
    run_process: Callable[[ProcessRequest], ProcessRecord], main: ProjectTasks
) -> ServedMilestones:
    if not any(read_task_field(task, MILESTONE) for task in main.by_name.values()):
        return NO_MILESTONE_SERVED
    active = tuple(
        read_entity(run_process, main.root, MILESTONE, name)
        for name in _list_milestones(run_process, main, ACTIVE_STATUS)
    )
    if not any(read_task_field(milestone, AFTER_FIELD) for milestone in active):
        return ServedMilestones(served=tuple(milestone.name for milestone in active), waiting=())
    reached = frozenset(MILESTONE_PREFIX + name for name in _list_milestones(run_process, main, REACHED_STATUS))
    after_not_reached = {milestone.name: _list_after_not_reached(milestone, reached) for milestone in active}
    return ServedMilestones(
        served=tuple(name for name, after in after_not_reached.items() if not after),
        waiting=tuple(
            WaitingMilestone(milestone=name, after=after) for name, after in after_not_reached.items() if after
        ),
    )
