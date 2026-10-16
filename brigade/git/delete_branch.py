from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

GIT_TIMEOUT_S = 10.0


def delete_branch(run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, branch: str) -> None:
    run_process(
        ProcessRequest(argv=("git", "branch", "--quiet", "-D", branch), cwd=str(repository), timeout_s=GIT_TIMEOUT_S)
    )
