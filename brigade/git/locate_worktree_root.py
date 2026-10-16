from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

READ_TIMEOUT_S = 10.0


def locate_worktree_root(run_process: Callable[[ProcessRequest], ProcessRecord], path: Path) -> Path:
    record = run_process(
        ProcessRequest(argv=("git", "rev-parse", "--show-toplevel"), cwd=str(path), timeout_s=READ_TIMEOUT_S)
    )
    return Path(record.stdout.strip())
