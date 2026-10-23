from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRecord, ProcessRequest

AWAWA_TIMEOUT_S = 300.0
SUCCESS = (0,)


def run_awawa(
    run_process: Callable[[ProcessRequest], ProcessRecord],
    cwd: Path,
    arguments: tuple[str, ...],
    acceptable_exit_codes: tuple[int, ...] = EVERY_EXIT_CODE,
) -> ProcessRecord:
    return run_process(
        ProcessRequest(
            argv=("awawa", *arguments),
            cwd=str(cwd),
            timeout_s=AWAWA_TIMEOUT_S,
            acceptable_exit_codes=acceptable_exit_codes,
        )
    )
