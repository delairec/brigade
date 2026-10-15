from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

GIT_TIMEOUT_S = 10.0
SHOWN_OR_ABSENT = (0, 128)


def read_file_at(run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, location: str) -> str:
    record = run_process(
        ProcessRequest(
            argv=("git", "cat-file", "-p", location),
            cwd=str(repository),
            timeout_s=GIT_TIMEOUT_S,
            acceptable_exit_codes=SHOWN_OR_ABSENT,
        )
    )
    return record.stdout
