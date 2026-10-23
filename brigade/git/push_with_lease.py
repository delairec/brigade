from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.git.push_branch import REMOTE
from brigade.git.timeouts import REMOTE_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest


@dataclass(frozen=True)
class LeasedPush:
    worktree: Path
    branch: str
    expected_head: str
    environment: dict


def push_with_lease(run_process: Callable[[ProcessRequest], ProcessRecord], push: LeasedPush) -> None:
    run_process(
        ProcessRequest(
            argv=(
                "git",
                "push",
                "--quiet",
                f"--force-with-lease={push.branch}:{push.expected_head}",
                REMOTE,
                f"HEAD:{push.branch}",
            ),
            cwd=str(push.worktree),
            timeout_s=REMOTE_TIMEOUT_S,
            environment=push.environment,
        )
    )
