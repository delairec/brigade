from collections.abc import Callable
from pathlib import Path

from brigade.git.timeouts import GIT_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest

RESOLVED_OR_NOT = (0, 1)
COMMIT_PEEL = "^{commit}"


def resolve_commit(run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, ref: str) -> str | None:
    record = run_process(
        ProcessRequest(
            argv=("git", "rev-parse", "--verify", "--quiet", "--end-of-options", f"{ref}{COMMIT_PEEL}"),
            cwd=str(repository),
            timeout_s=GIT_TIMEOUT_S,
            acceptable_exit_codes=RESOLVED_OR_NOT,
        )
    )
    return record.stdout.strip() or None
