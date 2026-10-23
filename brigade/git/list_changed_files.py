from collections.abc import Callable
from pathlib import Path

from brigade.git.timeouts import GIT_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest

STATUS_CODE_WIDTH = len("XY ")


def list_changed_files(run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path) -> tuple[str, ...]:
    record = run_process(
        ProcessRequest(
            argv=("git", "status", "--porcelain", "-z", "--no-renames", "--untracked-files=all"),
            cwd=str(repository),
            timeout_s=GIT_TIMEOUT_S,
        )
    )
    return tuple(entry[STATUS_CODE_WIDTH:] for entry in record.stdout.split("\0") if entry)
