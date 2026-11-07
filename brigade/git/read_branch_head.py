from collections.abc import Callable
from pathlib import Path

from brigade.git.timeouts import GIT_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest

STANDING = 0
STANDING_OR_NOT = (STANDING, 1)


def read_branch_head(
    run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, branch: str
) -> str | None:
    record = run_process(
        ProcessRequest(
            argv=("git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"),
            cwd=str(repository),
            timeout_s=GIT_TIMEOUT_S,
            acceptable_exit_codes=STANDING_OR_NOT,
        )
    )
    if record.exit_code != STANDING:
        return None
    return record.stdout.strip()
