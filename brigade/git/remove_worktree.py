from collections.abc import Callable
from pathlib import Path

from brigade.git.timeouts import TREE_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest


def remove_worktree(run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, worktree: Path) -> None:
    run_process(
        ProcessRequest(
            argv=("git", "worktree", "remove", "--force", str(worktree)),
            cwd=str(repository),
            timeout_s=TREE_TIMEOUT_S,
        )
    )
