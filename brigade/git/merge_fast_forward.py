from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

MERGE_TIMEOUT_S = 60.0


def merge_fast_forward(run_process: Callable[[ProcessRequest], ProcessRecord], worktree: Path, branch: str) -> None:
    run_process(
        ProcessRequest(
            argv=("git", "merge", "--quiet", "--ff-only", branch), cwd=str(worktree), timeout_s=MERGE_TIMEOUT_S
        )
    )
