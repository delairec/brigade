from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRecord, ProcessRequest

AWAWA_TIMEOUT_S = 300.0


def run_awawa(
    run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, arguments: tuple[str, ...]
) -> ProcessRecord:
    return run_process(
        ProcessRequest(
            argv=("awawa", *arguments),
            cwd=str(root),
            timeout_s=AWAWA_TIMEOUT_S,
            acceptable_exit_codes=EVERY_EXIT_CODE,
        )
    )
