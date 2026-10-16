import re

TASK_TYPE = "TASK"
TRAILING_NUMBER = re.compile(r"\d+$")


def count_next_task_number(entities: list) -> int:
    names = [entity["name"] for entity in entities if entity["type"] == TASK_TYPE]
    return max((int(digits) for name in names for digits in TRAILING_NUMBER.findall(name)), default=0) + 1
