import re
from dataclasses import dataclass

SPACE = " "
HYPHEN = "-"
PRECEDING_TYPES = ("feat", "fix")
TASK_NUMBER = re.compile(r"\d+")
TITLE_OF_NO_DELIVERY = "docs(milestone): report a milestone delivering no task"


@dataclass(frozen=True)
class DeliveredTask:
    name: str
    type: str
    component: str | None


@dataclass(frozen=True)
class Delivery:
    milestone: str
    subject: str
    tasks: tuple[DeliveredTask, ...]


def _read_task_number(task: DeliveredTask) -> int:
    return int(TASK_NUMBER.search(task.name).group())


def _choose_type(tasks: list[DeliveredTask]) -> str:
    types = [task.type for task in tasks]
    return next((preceding for preceding in PRECEDING_TYPES if preceding in types), types[0])


def _describe_scope(tasks: list[DeliveredTask]) -> str:
    components = {task.component for task in tasks}
    if len(components) != 1 or None in components:
        return ""
    return f"({components.pop().replace(SPACE, HYPHEN)})"


def compose_delivery_title(delivery: Delivery) -> str:
    if not delivery.tasks:
        return f"{TITLE_OF_NO_DELIVERY} ({delivery.milestone})"
    tasks = sorted(delivery.tasks, key=_read_task_number)
    return f"{_choose_type(tasks)}{_describe_scope(tasks)}: {delivery.subject} ({delivery.milestone})"
