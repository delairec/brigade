from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

READ_TIMEOUT_S = 10.0
REPOSITORY_OR_NOT = (0, 128)
INSIDE_A_REPOSITORY = 0


def detect_repository(run_process: Callable[[ProcessRequest], ProcessRecord], path: Path) -> bool:
    if not path.is_dir():
        return False
    record = run_process(
        ProcessRequest(
            argv=("git", "rev-parse", "--git-dir"),
            cwd=str(path),
            timeout_s=READ_TIMEOUT_S,
            acceptable_exit_codes=REPOSITORY_OR_NOT,
        )
    )
    return record.exit_code == INSIDE_A_REPOSITORY
