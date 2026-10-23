from collections.abc import Callable
from pathlib import Path

from brigade.git.timeouts import TREE_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest


def read_diff(
    run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, start: str, end: str
) -> ProcessRecord:
    return run_process(ProcessRequest(argv=("git", "diff", start, end), cwd=str(repository), timeout_s=TREE_TIMEOUT_S))
