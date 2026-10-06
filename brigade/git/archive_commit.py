from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

ARCHIVE_TIMEOUT_S = 300.0


def archive_commit(
    run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, sha: str, destination: Path
) -> None:
    run_process(
        ProcessRequest(
            argv=("git", "archive", "--format=tar", f"--output={destination}", sha),
            cwd=str(repository),
            timeout_s=ARCHIVE_TIMEOUT_S,
        )
    )
