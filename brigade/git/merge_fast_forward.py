from collections.abc import Callable
from pathlib import Path

from brigade.git.timeouts import TREE_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest


def merge_fast_forward(run_process: Callable[[ProcessRequest], ProcessRecord], worktree: Path, branch: str) -> None:
    run_process(
        ProcessRequest(
            argv=("git", "merge", "--quiet", "--ff-only", branch), cwd=str(worktree), timeout_s=TREE_TIMEOUT_S
        )
    )
