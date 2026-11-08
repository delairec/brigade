from collections.abc import Callable
from pathlib import Path

from brigade.git.add_branch_worktree import BranchWorktree
from brigade.git.add_worktree_on_branch import add_worktree_on_branch
from brigade.git.list_worktrees import list_worktrees
from brigade.git.reset_worktree import reset_worktree
from brigade.system.run_process import ProcessRecord, ProcessRequest


def open_branch_worktree(
    run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, worktree: BranchWorktree
) -> None:
    listed = list_worktrees(run_process, repository)
    if not any(found.path == worktree.path and found.branch == worktree.branch for found in listed):
        add_worktree_on_branch(run_process, repository, worktree)
    reset_worktree(run_process, worktree.path, worktree.start)
