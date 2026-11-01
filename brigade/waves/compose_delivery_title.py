import re

from brigade.waves.delivery import DeliveredTask, Delivery

TYPE_AND_SCOPE = re.compile(r"^[a-z]+(\([^)]*\))?!?: ")
TASK_NAMES = re.compile(r" \(@TASK\.[^)]*\)$")
TYPES_BY_PRECEDENCE = ("feat", "fix")
SUBJECT_SEPARATOR = "; "
NAME_SEPARATOR = ", "


def _strip_subject(task: DeliveredTask) -> str:
    return TASK_NAMES.sub("", TYPE_AND_SCOPE.sub("", task.pr_title))


def _choose_type(tasks: tuple[DeliveredTask, ...]) -> str:
    types = {task.type for task in tasks}
    return next((kind for kind in TYPES_BY_PRECEDENCE if kind in types), tasks[0].type)


def _describe_scope(tasks: tuple[DeliveredTask, ...]) -> str:
    components = {task.component for task in tasks}
    if len(components) != 1 or None in components:
        return ""
    return f"({components.pop().replace(' ', '-')})"


def _name_delivered(delivery: Delivery) -> str:
    tasks = tuple(f"@TASK.{task.name}" for task in delivery.tasks)
    milestone = (delivery.milestone.name,) if delivery.wave is None else ()
    return NAME_SEPARATOR.join((*milestone, *tasks))


def compose_delivery_title(delivery: Delivery) -> str:
    tasks = delivery.tasks
    if len(tasks) == 1:
        return f"{TASK_NAMES.sub('', tasks[0].pr_title)} ({_name_delivered(delivery)})"
    subjects = SUBJECT_SEPARATOR.join(_strip_subject(task) for task in tasks)
    return f"{_choose_type(tasks)}{_describe_scope(tasks)}: {subjects} ({_name_delivered(delivery)})"
