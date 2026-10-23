from collections.abc import Callable
from pathlib import Path

from brigade.git.timeouts import GIT_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest


def read_current_branch(run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path) -> str:
    record = run_process(
        ProcessRequest(argv=("git", "branch", "--show-current"), cwd=str(repository), timeout_s=GIT_TIMEOUT_S)
    )
    return record.stdout.strip()
