from dataclasses import dataclass
from pathlib import Path

from brigade.git.push_branch import BranchPush
from brigade.git.push_branch_with_lease import push_branch_with_lease
from brigade.git.read_current_branch import read_current_branch
from brigade.runtime import Runtime
from brigade.tasks.locate_task_worktree import locate_task_worktree
from brigade.tasks.require_passing_check import require_passing_check

DOCUMENT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class TaskPushDemand:
    path: Path
    task: str | None
    environment: dict


def push_task_branch(runtime: Runtime, demand: TaskPushDemand) -> dict:
    worktree = locate_task_worktree(runtime, demand.path, demand.task)
    check = require_passing_check(runtime, worktree)
    branch = read_current_branch(runtime.run_process, worktree.path)
    push_branch_with_lease(
        runtime.run_process, BranchPush(repository=worktree.path, branch=branch, environment=demand.environment)
    )
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "project": worktree.project.name,
        "task": worktree.task,
        "branch": branch,
        "head": check["head"],
    }
