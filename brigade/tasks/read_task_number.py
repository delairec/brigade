import re

from brigade.errors import BrigadeError

TASK_NUMBER = re.compile(r"\d+$")


def read_task_number(task: str, wave: str) -> int:
    number = TASK_NUMBER.search(task)
    if number is None:
        raise BrigadeError(f"@TASK.{task} of the wave {wave} carries no number to be ordered by")
    return int(number.group())
