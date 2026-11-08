from collections.abc import Callable
from pathlib import Path

from brigade.git.timeouts import GIT_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest


def read_head_subject(run_process: Callable[[ProcessRequest], ProcessRecord], worktree: Path) -> str:
    return run_process(
        ProcessRequest(argv=("git", "log", "-1", "--format=%s", "HEAD"), cwd=str(worktree), timeout_s=GIT_TIMEOUT_S)
    ).stdout.strip()
