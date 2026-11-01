from brigade.corpus.read_entities import Entity
from brigade.runtime import Runtime
from brigade.tasks.find_task_number import find_task_number
from brigade.tasks.read_task_after import read_task_after
from brigade.tasks.read_task_field import read_task_field
from brigade.waves.read_project_tasks import ProjectTasks

STATUS_FIELD = "STATUS"
TODO_STATUS = "todo"
MILESTONE = "MILESTONE"
MILESTONE_PREFIX = "@MILESTONE."
NAMING_NO_MILESTONE = ()


def _name_milestone(milestone: str | None) -> tuple[str, ...]:
    return NAMING_NO_MILESTONE if milestone is None else (MILESTONE_PREFIX + milestone,)


def _is_candidate(runtime: Runtime, tasks: ProjectTasks, task: Entity, open_tasks: dict[str, str]) -> bool:
    return (
        read_task_field(task, STATUS_FIELD) == (TODO_STATUS,)
        and read_task_field(task, MILESTONE) == _name_milestone(tasks.milestone)
        and find_task_number(task.name) is not None
        and task.name not in open_tasks
        and not runtime.read_live_blockers(runtime.run_process, tasks.root, task.name)
    )


def admit_candidates(runtime: Runtime, tasks: ProjectTasks, open_tasks: dict[str, str]) -> tuple[str, ...]:
    candidates = [task for task in tasks.by_name.values() if _is_candidate(runtime, tasks, task, open_tasks)]
    admitted: list[str] = []
    while True:
        ready = [
            task.name
            for task in candidates
            if task.name not in admitted
            and all(after in tasks.implemented or after in admitted for after in read_task_after(task))
        ]
        if not ready:
            return tuple(admitted)
        admitted.extend(ready)
