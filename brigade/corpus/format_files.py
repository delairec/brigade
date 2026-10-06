from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

AWAWA_TIMEOUT_S = 30.0


def format_files(run_process: Callable[[ProcessRequest], ProcessRecord], paths: tuple[Path, ...]) -> None:
    run_process(
        ProcessRequest(
            argv=("awawa", "fmt", *(str(path) for path in paths)), cwd=str(paths[0].parent), timeout_s=AWAWA_TIMEOUT_S
        )
    )
