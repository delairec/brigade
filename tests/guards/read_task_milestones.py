import re

_TASK_MILESTONE = re.compile(r"^TASK (\S+)$(?:\n\t.*$)*?\n\tMILESTONE @MILESTONE\.(\S+)$", re.MULTILINE)


def read_task_milestones(tasks: str) -> dict[str, str]:
    return dict(_TASK_MILESTONE.findall(tasks))
