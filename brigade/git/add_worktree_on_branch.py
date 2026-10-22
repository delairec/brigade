from collections.abc import Callable
from pathlib import Path

from brigade.git.add_branch_worktree import WORKTREE_TIMEOUT_S, BranchWorktree
from brigade.system.run_process import ProcessRecord, ProcessRequest


def add_worktree_on_branch(
    run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, worktree: BranchWorktree
) -> None:
    run_process(
        ProcessRequest(
            argv=("git", "worktree", "add", "--quiet", str(worktree.path), worktree.branch),
            cwd=str(repository),
            timeout_s=WORKTREE_TIMEOUT_S,
        )
    )
