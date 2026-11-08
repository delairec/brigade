from collections.abc import Callable
from pathlib import Path

from brigade.git.timeouts import TREE_TIMEOUT_S
from brigade.system.delete_path import delete_path
from brigade.system.run_process import ProcessRecord, ProcessRequest


def clear_worktree_path(
    run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, worktree: Path
) -> None:
    if worktree.exists():
        delete_path(worktree)
    run_process(ProcessRequest(argv=("git", "worktree", "prune"), cwd=str(repository), timeout_s=TREE_TIMEOUT_S))
