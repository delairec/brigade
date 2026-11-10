from brigade.corpus.read_entities import Entity
from brigade.runtime import Runtime
from brigade.tasks.find_task_number import find_task_number
from brigade.tasks.read_task_after import read_task_after
from brigade.waves.is_task_todo_of_reading import is_task_todo_of_reading
from brigade.waves.read_project_tasks import ProjectTasks


def _is_candidate(runtime: Runtime, tasks: ProjectTasks, task: Entity, unavailable_tasks: dict[str, str]) -> bool:
    return (
        is_task_todo_of_reading(tasks, task)
        and find_task_number(task.name) is not None
        and task.name not in unavailable_tasks
        and not runtime.read_live_blockers(runtime.run_process, tasks.root, task.name)
    )


def admit_candidates(runtime: Runtime, tasks: ProjectTasks, unavailable_tasks: dict[str, str]) -> tuple[str, ...]:
    candidates = [task for task in tasks.by_name.values() if _is_candidate(runtime, tasks, task, unavailable_tasks)]
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
