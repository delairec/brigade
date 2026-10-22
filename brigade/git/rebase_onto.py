from collections.abc import Callable
from pathlib import Path

from brigade.errors import CommandFailed
from brigade.system.run_process import ProcessRecord, ProcessRequest

REBASE_TIMEOUT_S = 120.0
APPLIED_OR_STOPPED = (0, 1)
FOUND_OR_ABSENT = (0, 1)
REBASE_IN_PROGRESS = 0


def rebase_onto(run_process: Callable[[ProcessRequest], ProcessRecord], worktree: Path, upstream: str) -> bool:
    rebased = run_process(
        ProcessRequest(
            argv=("git", "rebase", upstream),
            cwd=str(worktree),
            timeout_s=REBASE_TIMEOUT_S,
            acceptable_exit_codes=APPLIED_OR_STOPPED,
        )
    )
    if rebased.exit_code == 0:
        return True
    stopped_at = run_process(
        ProcessRequest(
            argv=("git", "rev-parse", "--quiet", "--verify", "REBASE_HEAD"),
            cwd=str(worktree),
            timeout_s=REBASE_TIMEOUT_S,
            acceptable_exit_codes=FOUND_OR_ABSENT,
        )
    )
    if stopped_at.exit_code != REBASE_IN_PROGRESS:
        raise CommandFailed(rebased.argv, rebased.exit_code, rebased.stderr)
    run_process(ProcessRequest(argv=("git", "rebase", "--abort"), cwd=str(worktree), timeout_s=REBASE_TIMEOUT_S))
    return False
