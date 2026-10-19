from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

FETCH_TIMEOUT_S = 60.0
THIS_REPOSITORY = "."


def fast_forward_branch(
    run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, branch: str, target: str
) -> None:
    run_process(
        ProcessRequest(
            argv=("git", "fetch", "--quiet", THIS_REPOSITORY, f"{target}:{branch}"),
            cwd=str(repository),
            timeout_s=FETCH_TIMEOUT_S,
        )
    )
