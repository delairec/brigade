from collections.abc import Callable
from pathlib import Path

from brigade.git.timeouts import GIT_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest


def is_on_a_remote(run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, commit: str) -> bool:
    record = run_process(
        ProcessRequest(
            argv=("git", "for-each-ref", "--count=1", "--contains", commit, "--format=%(refname)", "refs/remotes"),
            cwd=str(repository),
            timeout_s=GIT_TIMEOUT_S,
        )
    )
    return bool(record.stdout.strip())
