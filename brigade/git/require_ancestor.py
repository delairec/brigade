from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

GIT_TIMEOUT_S = 10.0


def require_ancestor(run_process: Callable[[ProcessRequest], ProcessRecord], worktree: Path, ancestor: str) -> None:
    run_process(
        ProcessRequest(
            argv=("git", "merge-base", "--is-ancestor", ancestor, "HEAD"), cwd=str(worktree), timeout_s=GIT_TIMEOUT_S
        )
    )
