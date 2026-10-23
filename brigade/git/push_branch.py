from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.git.timeouts import REMOTE_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest

REMOTE = "origin"


@dataclass(frozen=True)
class BranchPush:
    repository: Path
    branch: str
    environment: dict


def push_branch(run_process: Callable[[ProcessRequest], ProcessRecord], push: BranchPush) -> None:
    run_process(
        ProcessRequest(
            argv=("git", "push", "--quiet", REMOTE, push.branch),
            cwd=str(push.repository),
            timeout_s=REMOTE_TIMEOUT_S,
            environment=push.environment,
        )
    )
