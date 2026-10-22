from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

GIT_TIMEOUT_S = 10.0


def read_head(run_process: Callable[[ProcessRequest], ProcessRecord], worktree: Path) -> str:
    return run_process(
        ProcessRequest(argv=("git", "rev-parse", "HEAD"), cwd=str(worktree), timeout_s=GIT_TIMEOUT_S)
    ).stdout.strip()
