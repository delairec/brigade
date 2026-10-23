from collections.abc import Callable
from pathlib import Path

from brigade.git.timeouts import GIT_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest


def create_branch(run_process: Callable[[ProcessRequest], ProcessRecord], worktree: Path, branch: str) -> None:
    run_process(
        ProcessRequest(
            argv=("git", "switch", "--quiet", "--create", branch), cwd=str(worktree), timeout_s=GIT_TIMEOUT_S
        )
    )
