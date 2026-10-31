from collections.abc import Callable
from pathlib import Path

from brigade.git.timeouts import GIT_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest


def reset_worktree(run_process: Callable[[ProcessRequest], ProcessRecord], worktree: Path, start: str) -> None:
    run_process(
        ProcessRequest(argv=("git", "reset", "--quiet", "--hard", start), cwd=str(worktree), timeout_s=GIT_TIMEOUT_S)
    )
