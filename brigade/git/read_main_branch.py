from collections.abc import Callable
from pathlib import Path

from brigade.git.read_current_branch import read_current_branch
from brigade.system.run_process import ProcessRecord, ProcessRequest

READ_TIMEOUT_S = 10.0
SYMBOLIC_OR_NOT = (0, 1)
REMOTE_PREFIX = "origin/"


def _read_origin_head(run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path) -> str:
    record = run_process(
        ProcessRequest(
            argv=("git", "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"),
            cwd=str(repository),
            timeout_s=READ_TIMEOUT_S,
            acceptable_exit_codes=SYMBOLIC_OR_NOT,
        )
    )
    return record.stdout.strip().removeprefix(REMOTE_PREFIX)


def read_main_branch(run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path) -> str | None:
    branch = _read_origin_head(run_process, repository) or read_current_branch(run_process, repository)
    return branch or None
