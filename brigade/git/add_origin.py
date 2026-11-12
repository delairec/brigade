from collections.abc import Callable
from pathlib import Path

from brigade.git.timeouts import GIT_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest


def add_origin(run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, url: str) -> None:
    run_process(
        ProcessRequest(argv=("git", "remote", "add", "origin", url), cwd=str(repository), timeout_s=GIT_TIMEOUT_S)
    )
