import re
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entities import Entity, read_entities
from brigade.errors import BrigadeError
from brigade.git.locate_main_checkout import locate_main_checkout
from brigade.git.locate_worktree_root import locate_worktree_root
from brigade.git.read_current_branch import read_current_branch
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runtime import Runtime
from brigade.waves.describe_request import describe_request

TASK_BRANCH = re.compile(r"task/(?P<slug>.+)/(?P<task>[^/]+)")
WAVE_BRANCH_PREFIX = "integration/"
REQUEST_TYPE = "REQUEST"


@dataclass(frozen=True)
class TaskWorktree:
    path: Path
    task: str
    project: Entity
    wave: dict


def locate_task_worktree(runtime: Runtime, path: Path, named_task: str | None) -> TaskWorktree:
    root = locate_worktree_root(runtime.run_process, path)
    branch = read_current_branch(runtime.run_process, root)
    parts = TASK_BRANCH.fullmatch(branch)
    if parts is None:
        raise BrigadeError(f"the branch {branch} is not a task/<slug>/<task> branch")
    if named_task is not None and named_task != parts["task"]:
        raise BrigadeError(f"@TASK.{named_task} is not the task of the branch {branch}")
    project = require_project_at(read_projects(runtime), locate_main_checkout(runtime.run_process, root))
    wave_branch = f"{WAVE_BRANCH_PREFIX}{parts['slug']}"
    requests = read_entities(
        runtime.run_process,
        runtime.paths.config_root,
        REQUEST_TYPE,
        f"PROJECT==@PROJECT.{project.name}",
        f"BRANCH=={wave_branch}",
    )
    if not requests:
        raise BrigadeError(f"no {REQUEST_TYPE} of @PROJECT.{project.name} has the BRANCH {wave_branch}")
    return TaskWorktree(path=root, task=parts["task"], project=project, wave=describe_request(requests[0]))
