from collections.abc import Callable
from pathlib import Path

from brigade.git.timeouts import TREE_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest


def add_detached_worktree(
    run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, worktree: Path, start: str
) -> None:
    run_process(
        ProcessRequest(
            argv=("git", "worktree", "add", "--quiet", "--detach", str(worktree), start),
            cwd=str(repository),
            timeout_s=TREE_TIMEOUT_S,
        )
    )
