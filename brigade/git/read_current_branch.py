from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

READ_TIMEOUT_S = 10.0


def read_current_branch(run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path) -> str:
    record = run_process(
        ProcessRequest(argv=("git", "branch", "--show-current"), cwd=str(repository), timeout_s=READ_TIMEOUT_S)
    )
    return record.stdout.strip()
