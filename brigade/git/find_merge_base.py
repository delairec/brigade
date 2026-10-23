from collections.abc import Callable
from pathlib import Path

from brigade.git.timeouts import GIT_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest


def find_merge_base(
    run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, first: str, second: str
) -> str:
    record = run_process(
        ProcessRequest(
            argv=("git", "merge-base", "--end-of-options", first, second),
            cwd=str(repository),
            timeout_s=GIT_TIMEOUT_S,
        )
    )
    return record.stdout.strip()
