from collections.abc import Callable

from brigade.git.add_detached_worktree import DetachedWorktree
from brigade.git.timeouts import TREE_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest


def remove_detached_worktree(
    run_process: Callable[[ProcessRequest], ProcessRecord], worktree: DetachedWorktree
) -> None:
    run_process(
        ProcessRequest(
            argv=("git", "worktree", "remove", "--force", "--force", str(worktree.path)),
            cwd=str(worktree.repository),
            timeout_s=TREE_TIMEOUT_S,
        )
    )
