from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

READ_TIMEOUT_S = 10.0
ORIGIN_PRESENT_OR_ABSENT = (0, 2)


def read_origin_url(run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path) -> str | None:
    record = run_process(
        ProcessRequest(
            argv=("git", "remote", "get-url", "origin"),
            cwd=str(repository),
            timeout_s=READ_TIMEOUT_S,
            acceptable_exit_codes=ORIGIN_PRESENT_OR_ABSENT,
        )
    )
    return record.stdout.strip() or None
