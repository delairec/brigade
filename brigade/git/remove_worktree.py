from pathlib import Path
from typing import Callable

from brigade.system.run_process import ProcessRecord, ProcessRequest

WORKTREE_TIMEOUT_S = 60.0


def remove_worktree(run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, worktree: Path) -> None:
    run_process(
        ProcessRequest(
            argv=("git", "worktree", "remove", "--force", str(worktree)),
            cwd=str(repository),
            timeout_s=WORKTREE_TIMEOUT_S,
        )
    )
