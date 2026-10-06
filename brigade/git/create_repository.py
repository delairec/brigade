from pathlib import Path
from typing import Callable

from brigade.system.run_process import ProcessRecord, ProcessRequest

INIT_TIMEOUT_S = 10.0


def create_repository(run_process: Callable[[ProcessRequest], ProcessRecord], path: Path) -> None:
    run_process(ProcessRequest(argv=("git", "init", "--quiet"), cwd=str(path), timeout_s=INIT_TIMEOUT_S))
