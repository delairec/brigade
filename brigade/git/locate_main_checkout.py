from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

READ_TIMEOUT_S = 10.0


def locate_main_checkout(run_process: Callable[[ProcessRequest], ProcessRecord], worktree: Path) -> Path:
    record = run_process(
        ProcessRequest(
            argv=("git", "rev-parse", "--path-format=absolute", "--git-common-dir"),
            cwd=str(worktree),
            timeout_s=READ_TIMEOUT_S,
        )
    )
    return Path(record.stdout.strip()).parent
