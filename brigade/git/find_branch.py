from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

GIT_TIMEOUT_S = 10.0
FOUND = 0
FOUND_OR_NOT = (FOUND, 1)


def find_branch(run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, branch: str) -> bool:
    record = run_process(
        ProcessRequest(
            argv=("git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"),
            cwd=str(repository),
            timeout_s=GIT_TIMEOUT_S,
            acceptable_exit_codes=FOUND_OR_NOT,
        )
    )
    return record.exit_code == FOUND
