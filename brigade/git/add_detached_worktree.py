from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

WORKTREE_TIMEOUT_S = 60.0


def add_detached_worktree(
    run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, worktree: Path
) -> None:
    run_process(
        ProcessRequest(
            argv=("git", "worktree", "add", "--quiet", "--detach", str(worktree), "HEAD"),
            cwd=str(repository),
            timeout_s=WORKTREE_TIMEOUT_S,
        )
    )
