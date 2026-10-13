from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

PUSH_TIMEOUT_S = 120.0
REMOTE = "origin"


def push_branch(run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, branch: str) -> None:
    run_process(
        ProcessRequest(argv=("git", "push", "--quiet", REMOTE, branch), cwd=str(repository), timeout_s=PUSH_TIMEOUT_S)
    )
