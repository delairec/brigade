from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entity import read_entity
from brigade.registry.read_project_field import read_project_field
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.tick.read_implemented_tasks import read_implemented_tasks
from brigade.waves.compose_delivery_title import DeliveredTask, Delivery, compose_delivery_title

TASK_TYPE = "TASK"
MILESTONE_TYPE = "MILESTONE"
MILESTONE_PREFIX = "@MILESTONE."


@dataclass(frozen=True)
class MilestoneTitleDemand:
    run_process: Callable[[ProcessRequest], ProcessRecord]
    root: Path
    milestone: str


def compose_milestone_title(demand: MilestoneTitleDemand) -> str:
    milestone = read_entity(demand.run_process, demand.root, MILESTONE_TYPE, demand.milestone)
    implemented = (
        read_entity(demand.run_process, demand.root, TASK_TYPE, name)
        for name in read_implemented_tasks(demand.run_process, demand.root)
    )
    tasks = tuple(
        DeliveredTask(
            name=task.name, type=read_project_field(task, "TYPE"), component=read_project_field(task, "COMPONENT")
        )
        for task in implemented
        if read_project_field(task, "MILESTONE") == MILESTONE_PREFIX + demand.milestone
    )
    subject = read_project_field(milestone, "SUBJECT") or read_project_field(milestone, "TITLE")
    return compose_delivery_title(Delivery(milestone=demand.milestone, subject=subject, tasks=tasks))
