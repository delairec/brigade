from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

PUSH_TIMEOUT_S = 120.0
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
            timeout_s=PUSH_TIMEOUT_S,
            environment=push.environment,
        )
    )
