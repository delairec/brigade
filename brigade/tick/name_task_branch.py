WAVE_BRANCH_PREFIX = "integration/"
TASK_BRANCH_PREFIX = "task/"


def name_task_branch(wave_branch: str, task: str) -> str:
    return f"{TASK_BRANCH_PREFIX}{wave_branch.removeprefix(WAVE_BRANCH_PREFIX)}/{task}"
