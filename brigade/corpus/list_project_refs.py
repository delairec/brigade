from collections.abc import Callable
from pathlib import Path

from brigade.corpus.read_entity import Entity
from brigade.git.list_local_branches import list_local_branches
from brigade.git.list_worktrees import list_worktrees
from brigade.system.run_process import ProcessRecord, ProcessRequest

REPOSITORY_FIELD = "PATH"
MAIN_FIELD = "MAIN"
WORKTREE_PREFIX = "worktree:"


def _read_field(project: Entity, name: str) -> str | None:
    return next((field.value for field in project.fields if field.name == name), None)


def list_project_refs(run_process: Callable[[ProcessRequest], ProcessRecord], project: Entity) -> list[str]:
    repository = Path(_read_field(project, REPOSITORY_FIELD))
    main = _read_field(project, MAIN_FIELD)
    branches = list_local_branches(run_process, repository)
    ordered = sorted(branches, key=lambda branch: branch != main)
    linked = list_worktrees(run_process, repository)[1:]
    return [*ordered, *(f"{WORKTREE_PREFIX}{worktree.branch}" for worktree in linked if worktree.branch is not None)]
