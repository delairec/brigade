from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

REBASE_TIMEOUT_S = 120.0
APPLIED_OR_CONFLICTING = (0, 1)


def rebase_onto(run_process: Callable[[ProcessRequest], ProcessRecord], worktree: Path, upstream: str) -> bool:
    rebased = run_process(
        ProcessRequest(
            argv=("git", "rebase", upstream),
            cwd=str(worktree),
            timeout_s=REBASE_TIMEOUT_S,
            acceptable_exit_codes=APPLIED_OR_CONFLICTING,
        )
    )
    if rebased.exit_code == 0:
        return True
    run_process(ProcessRequest(argv=("git", "rebase", "--abort"), cwd=str(worktree), timeout_s=REBASE_TIMEOUT_S))
    return False
