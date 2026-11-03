import re
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entity import Entity
from brigade.errors import BrigadeError
from brigade.git.locate_main_checkout import locate_main_checkout
from brigade.git.locate_worktree_root import locate_worktree_root
from brigade.git.read_current_branch import read_current_branch
from brigade.ledger.read_ledger import read_ledger
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runtime import Runtime
from brigade.tasks.find_task_base import find_task_base
from brigade.waves.map_open_tasks import map_open_tasks

TASK_BRANCH = re.compile(
    r"(?P<prefix>build|chore|ci|docs|feature|fix|perf|refactor|revert|style|test)/(?P<task>[^/-]+)-(?P<slug>[a-z0-9-]*)"
)


@dataclass(frozen=True)
class TaskWorktree:
    path: Path
    task: str
    project: Entity
    wave: str
    base: str


def locate_task_worktree(runtime: Runtime, path: Path, named_task: str | None) -> TaskWorktree:
    root = locate_worktree_root(runtime.run_process, path)
    branch = read_current_branch(runtime.run_process, root)
    parts = TASK_BRANCH.fullmatch(branch)
    if parts is None:
        raise BrigadeError(f"the branch {branch} is not a <prefix>/<task>-<slug> branch")
    task = parts["task"]
    if named_task is not None and named_task != task:
        raise BrigadeError(f"@TASK.{named_task} is not the task of the branch {branch}")
    project = require_project_at(read_projects(runtime), locate_main_checkout(runtime.run_process, root))
    entries = read_ledger(runtime.paths.state_root).entries
    wave = map_open_tasks(entries, project.name).get(task)
    if wave is None:
        raise BrigadeError(f"no open wave of @PROJECT.{project.name} holds @TASK.{task}")
    base = find_task_base(runtime, root, project, task)
    return TaskWorktree(path=root, task=task, project=project, wave=wave, base=base)
