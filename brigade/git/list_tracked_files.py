from collections.abc import Callable
from pathlib import Path

from brigade.git.timeouts import GIT_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest


def list_tracked_files(
    run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, pathspec: str
) -> tuple[str, ...]:
    record = run_process(
        ProcessRequest(argv=("git", "ls-files", "-z", "--", pathspec), cwd=str(repository), timeout_s=GIT_TIMEOUT_S)
    )
    return tuple(file for file in record.stdout.split("\0") if file)
