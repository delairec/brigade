from collections.abc import Callable
from pathlib import Path

from brigade.git.push_branch import PUSH_TIMEOUT_S, REMOTE
from brigade.system.run_process import ProcessRecord, ProcessRequest


def force_push_branch(run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, branch: str) -> None:
    run_process(
        ProcessRequest(
            argv=("git", "push", "--quiet", "--force", REMOTE, branch), cwd=str(repository), timeout_s=PUSH_TIMEOUT_S
        )
    )
