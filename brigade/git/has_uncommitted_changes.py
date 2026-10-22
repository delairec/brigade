from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

READ_TIMEOUT_S = 10.0


def has_uncommitted_changes(run_process: Callable[[ProcessRequest], ProcessRecord], worktree: Path) -> bool:
    record = run_process(
        ProcessRequest(
            argv=("git", "status", "--porcelain", "--untracked-files=no"),
            cwd=str(worktree),
            timeout_s=READ_TIMEOUT_S,
        )
    )
    return bool(record.stdout)
