from brigade.tasks.read_task_number import TASK_NUMBER


def find_task_number(task: str) -> int | None:
    number = TASK_NUMBER.search(task)
    if number is None:
        return None
    return int(number.group())
