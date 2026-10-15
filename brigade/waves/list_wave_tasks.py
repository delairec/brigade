import argparse

from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.read_entities import read_entities
from brigade.errors import BrigadeError
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.task_state import TaskState
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime
from brigade.system.read_configuration import Configuration

TASK_TYPE = "TASK"
QUEUED_STATE = "queued"


def _read_states(runtime: Runtime, milestone: str) -> dict[str, str]:
    return {
        entry.event.task: entry.event.state
        for entry in read_ledger(runtime.paths.state_root).entries
        if isinstance(entry.event, TaskState) and entry.event.wave == milestone
    }


def _read_pull_request(delivered_by: str | None) -> int | None:
    return None if delivered_by is None else int(delivered_by)


def list_wave_tasks(runtime: Runtime, configuration: Configuration, request: dict) -> list[dict]:
    if request["branch"] is None:
        return []
    project = find_project(read_projects(runtime), request["project"])
    if read_project_field(project, "CORPUS") is None:
        raise BrigadeError(f"@PROJECT.{project.name} declares no corpus")
    query = argparse.Namespace(project=request["project"], ref=request["branch"], worktree=None)
    tree = prepare_project_tree(query, configuration, runtime)
    states = _read_states(runtime, request["milestone"])
    tasks = read_entities(runtime.run_process, tree.root, TASK_TYPE, f"MILESTONE==@MILESTONE.{request['milestone']}")
    return [
        {
            "task": task.name,
            "title": read_project_field(task, "TITLE"),
            "state": states.get(task.name, QUEUED_STATE),
            "pull_request": _read_pull_request(read_project_field(task, "DELIVERED_BY")),
        }
        for task in tasks
    ]
