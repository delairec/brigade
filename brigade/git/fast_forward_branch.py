from collections.abc import Callable
from pathlib import Path

from brigade.git.timeouts import TREE_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest

THIS_REPOSITORY = "."


def fast_forward_branch(
    run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, branch: str, target: str
) -> None:
    run_process(
        ProcessRequest(
            argv=("git", "fetch", "--quiet", THIS_REPOSITORY, f"{target}:{branch}"),
            cwd=str(repository),
            timeout_s=TREE_TIMEOUT_S,
        )
    )
