from brigade.errors import BrigadeError
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime
from brigade.system.read_configuration import Configuration
from brigade.tasks.read_milestone_tasks import read_milestone_tasks
from brigade.waves.prepare_wave_tree import prepare_wave_tree
from brigade.waves.read_task_states import read_task_states

QUEUED_STATE = "queued"


def _read_pull_request(delivered_by: str | None) -> int | None:
    return None if delivered_by is None else int(delivered_by)


def list_wave_tasks(runtime: Runtime, configuration: Configuration, request: dict) -> list[dict]:
    if request["branch"] is None:
        return []
    project = find_project(read_projects(runtime), request["project"])
    if read_project_field(project, "CORPUS") is None:
        raise BrigadeError(f"@PROJECT.{project.name} declares no corpus")
    tree = prepare_wave_tree(runtime, configuration, request)
    states = read_task_states(runtime.paths.state_root, request["wave"])
    tasks = read_milestone_tasks(runtime.run_process, tree.root, request["milestone"])
    return [
        {
            "task": task.name,
            "title": read_project_field(task, "TITLE"),
            "state": states.get(task.name, QUEUED_STATE),
            "pull_request": _read_pull_request(read_project_field(task, "DELIVERED_BY")),
        }
        for task in tasks
    ]
