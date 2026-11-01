from collections.abc import Callable
from pathlib import Path

from brigade.git.timeouts import GIT_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest


def list_local_branches(run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path) -> tuple[str, ...]:
    record = run_process(
        ProcessRequest(
            argv=("git", "for-each-ref", "--format=%(refname:lstrip=2)", "refs/heads"),
            cwd=str(repository),
            timeout_s=GIT_TIMEOUT_S,
        )
    )
    return tuple(record.stdout.splitlines())
