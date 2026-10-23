from collections.abc import Callable
from pathlib import Path

from brigade.git.timeouts import GIT_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest


def create_repository(run_process: Callable[[ProcessRequest], ProcessRecord], path: Path) -> None:
    run_process(ProcessRequest(argv=("git", "init", "--quiet"), cwd=str(path), timeout_s=GIT_TIMEOUT_S))
