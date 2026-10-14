import argparse
import json
from pathlib import Path

from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.read_entity import read_entity
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.task_state import TaskState
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime
from brigade.system.read_configuration import Configuration
from brigade.system.run_process import ProcessRequest

AWAWA_TIMEOUT_S = 30.0
TASK_TYPE = "TASK"
QUEUED_STATE = "queued"


def _read_states(runtime: Runtime, milestone: str) -> dict[str, str]:
    return {
        entry.event.task: entry.event.state
        for entry in read_ledger(runtime.paths.state_root).entries
        if isinstance(entry.event, TaskState) and entry.event.wave == milestone
    }


def _list_task_names(runtime: Runtime, corpus: Path, milestone: str) -> list[str]:
    record = runtime.run_process(
        ProcessRequest(
            argv=("awawa", "status", TASK_TYPE, "--where", f"MILESTONE==@MILESTONE.{milestone}", "--json", str(corpus)),
            cwd=str(corpus),
            timeout_s=AWAWA_TIMEOUT_S,
        )
    )
    return sorted(entity["name"] for entity in json.loads(record.stdout)["entities"] if entity["type"] == TASK_TYPE)


def _read_pull_request(delivered_by: str | None) -> int | None:
    return None if delivered_by is None else int(delivered_by)


def list_wave_tasks(runtime: Runtime, configuration: Configuration, request: dict) -> list[dict]:
    if request["branch"] is None:
        return []
    project = find_project(read_projects(runtime), request["project"])
    query = argparse.Namespace(project=request["project"], ref=request["branch"], worktree=None)
    tree = prepare_project_tree(query, configuration, runtime)
    corpus = tree.root / read_project_field(project, "CORPUS")
    states = _read_states(runtime, request["milestone"])
    tasks = [
        read_entity(runtime.run_process, corpus, TASK_TYPE, name)
        for name in _list_task_names(runtime, corpus, request["milestone"])
    ]
    return [
        {
            "task": task.name,
            "title": read_project_field(task, "TITLE"),
            "state": states.get(task.name, QUEUED_STATE),
            "pull_request": _read_pull_request(read_project_field(task, "DELIVERED_BY")),
        }
        for task in tasks
    ]
