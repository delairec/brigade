from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

DIFF_TIMEOUT_S = 60.0


def read_diff(
    run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, start: str, end: str
) -> ProcessRecord:
    return run_process(ProcessRequest(argv=("git", "diff", start, end), cwd=str(repository), timeout_s=DIFF_TIMEOUT_S))
