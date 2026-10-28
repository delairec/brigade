from collections.abc import Callable

from brigade.git.add_branch_worktree import BranchWorktree
from brigade.git.timeouts import TREE_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest


def switch_worktree_to_new_branch(
    run_process: Callable[[ProcessRequest], ProcessRecord], worktree: BranchWorktree
) -> None:
    run_process(
        ProcessRequest(
            argv=("git", "switch", "--quiet", "--create", worktree.branch, worktree.start),
            cwd=str(worktree.path),
            timeout_s=TREE_TIMEOUT_S,
        )
    )
