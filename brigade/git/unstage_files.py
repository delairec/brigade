from collections.abc import Callable
from pathlib import Path

from brigade.git.timeouts import GIT_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest


def unstage_files(
    run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, files: tuple[str, ...]
) -> None:
    run_process(
        ProcessRequest(argv=("git", "reset", "--quiet", "--", *files), cwd=str(repository), timeout_s=GIT_TIMEOUT_S)
    )
