from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entity import read_entity
from brigade.registry.read_project_field import read_project_field
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.tick.read_implemented_tasks import read_implemented_tasks
from brigade.waves.compose_delivery_title import DeliveredTask, Delivery, compose_delivery_title

TASK_TYPE = "TASK"
MILESTONE_PREFIX = "@MILESTONE."


@dataclass(frozen=True)
class MilestoneTitleDemand:
    run_process: Callable[[ProcessRequest], ProcessRecord]
    root: Path
    milestone: str
    read_pull_request_title: Callable[[int], str]


def compose_milestone_title(demand: MilestoneTitleDemand) -> str:
    implemented = (
        read_entity(demand.run_process, demand.root, TASK_TYPE, name)
        for name in read_implemented_tasks(demand.run_process, demand.root)
    )
    tasks = tuple(
        DeliveredTask(
            name=task.name,
            type=read_project_field(task, "TYPE"),
            component=read_project_field(task, "COMPONENT"),
            pull_request_title=demand.read_pull_request_title(int(read_project_field(task, "DELIVERED_BY"))),
        )
        for task in implemented
        if read_project_field(task, "MILESTONE") == MILESTONE_PREFIX + demand.milestone
    )
    return compose_delivery_title(Delivery(milestone=demand.milestone, tasks=tasks))
