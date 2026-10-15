from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

WORKTREE_TIMEOUT_S = 60.0


@dataclass(frozen=True)
class BranchWorktree:
    path: Path
    branch: str
    start: str


def add_branch_worktree(
    run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, worktree: BranchWorktree
) -> None:
    run_process(
        ProcessRequest(
            argv=("git", "worktree", "add", "--quiet", "-b", worktree.branch, str(worktree.path), worktree.start),
            cwd=str(repository),
            timeout_s=WORKTREE_TIMEOUT_S,
        )
    )
