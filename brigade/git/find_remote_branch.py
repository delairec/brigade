from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

LS_REMOTE_TIMEOUT_S = 60.0
REMOTE = "origin"
FOUND = 0
NOT_FOUND = 2


@dataclass(frozen=True)
class RemoteBranch:
    repository: Path
    branch: str
    environment: dict


def find_remote_branch(run_process: Callable[[ProcessRequest], ProcessRecord], remote_branch: RemoteBranch) -> bool:
    record = run_process(
        ProcessRequest(
            argv=(
                "git",
                "ls-remote",
                "--quiet",
                "--exit-code",
                "--heads",
                REMOTE,
                f"refs/heads/{remote_branch.branch}",
            ),
            cwd=str(remote_branch.repository),
            timeout_s=LS_REMOTE_TIMEOUT_S,
            acceptable_exit_codes=(FOUND, NOT_FOUND),
            environment=remote_branch.environment,
        )
    )
    return record.exit_code == FOUND
