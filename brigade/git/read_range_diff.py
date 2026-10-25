from collections.abc import Callable
from pathlib import Path

from brigade.git.timeouts import TREE_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest


def read_range_diff(
    run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, first: str, second: str
) -> ProcessRecord:
    return run_process(
        ProcessRequest(argv=("git", "range-diff", first, second), cwd=str(repository), timeout_s=TREE_TIMEOUT_S)
    )
