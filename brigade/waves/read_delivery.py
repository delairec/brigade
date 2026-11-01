import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entity import Entity, read_entity
from brigade.git.list_commit_subjects import list_commit_subjects
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.tasks.read_task_field import read_task_field
from brigade.tick.read_implemented_tasks import read_implemented_tasks
from brigade.waves.delivery import DeliveredMilestone, DeliveredTask, Delivery
from brigade.waves.merged_wave import MergedWave

TASK_TYPE = "TASK"
MILESTONE_TYPE = "MILESTONE"
TASK_NUMBER = re.compile(r"\d+")


@dataclass(frozen=True)
class DeliveryDemand:
    wave: str | None
    milestone: str | None
    base: str
    base_ref: str
    head: str
    report: str | None
    merged_waves: tuple[MergedWave, ...]
    attribution: tuple[str, ...]
    repository: Path
    read_tree: Callable[[str], Path]
    read_pull_request: Callable[[int], dict]


def _order_by_number(name: str) -> int:
    return int(TASK_NUMBER.search(name).group())


def _read_field(entity: Entity, name: str) -> str | None:
    return next(iter(read_task_field(entity, name)), None)


def _read_delivered_task(task: Entity, read_pull_request: Callable[[int], dict]) -> DeliveredTask:
    pr = int(_read_field(task, "DELIVERED_BY"))
    pull_request = read_pull_request(pr)
    return DeliveredTask(
        name=task.name,
        title=_read_field(task, "TITLE"),
        type=_read_field(task, "TYPE"),
        component=_read_field(task, "COMPONENT"),
        pr=pr,
        pr_title=pull_request["title"],
        pr_commits=tuple(pull_request["commits"]),
    )


def _read_milestone(run_process: Callable, root: Path, milestone: str | None) -> DeliveredMilestone | None:
    if milestone is None:
        return None
    return DeliveredMilestone(
        name=milestone, title=_read_field(read_entity(run_process, root, MILESTONE_TYPE, milestone), "TITLE")
    )


def _read_report(root: Path, report: str | None) -> str | None:
    if report is None or not (root / report).is_file():
        return None
    return (root / report).read_text(encoding="utf-8")


def read_delivery(run_process: Callable[[ProcessRequest], ProcessRecord], demand: DeliveryDemand) -> Delivery:
    head_root = demand.read_tree(demand.head)
    at_base = set(read_implemented_tasks(run_process, demand.read_tree(demand.base_ref)))
    delivered = sorted(
        (name for name in read_implemented_tasks(run_process, head_root) if name not in at_base), key=_order_by_number
    )
    return Delivery(
        wave=demand.wave,
        milestone=_read_milestone(run_process, head_root, demand.milestone),
        base=demand.base,
        merged_waves=demand.merged_waves,
        tasks=tuple(
            _read_delivered_task(read_entity(run_process, head_root, TASK_TYPE, name), demand.read_pull_request)
            for name in delivered
        ),
        commits=list_commit_subjects(run_process, demand.repository, demand.base_ref, demand.head),
        attribution=demand.attribution,
        report=_read_report(head_root, demand.report),
    )
