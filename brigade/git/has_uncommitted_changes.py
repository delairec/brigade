from collections.abc import Callable
from pathlib import Path

from brigade.git.timeouts import GIT_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest


def has_uncommitted_changes(run_process: Callable[[ProcessRequest], ProcessRecord], worktree: Path) -> bool:
    record = run_process(
        ProcessRequest(
            argv=("git", "status", "--porcelain", "--untracked-files=no"),
            cwd=str(worktree),
            timeout_s=GIT_TIMEOUT_S,
        )
    )
    return bool(record.stdout)
