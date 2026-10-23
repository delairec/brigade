from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.git.timeouts import GIT_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest

CURRENT_BRANCH_MARK = "*"
BRANCH_FORMAT = "--format=%(HEAD)%09%(objectname:short)%09%(upstream:short)"
FIELD_SEPARATOR = "\t"
NO_CURRENT_BRANCH = ("", "")


@dataclass(frozen=True)
class UpstreamLag:
    commit: str
    upstream: str
    upstream_commit: str
    behind: int


def _read(run_process: Callable[[ProcessRequest], ProcessRecord], checkout: Path, *arguments: str) -> str:
    record = run_process(ProcessRequest(argv=("git", *arguments), cwd=str(checkout), timeout_s=GIT_TIMEOUT_S))
    return record.stdout


def _find_current_branch(branches: str) -> tuple[str, str]:
    for line in branches.splitlines():
        mark, commit, upstream = line.split(FIELD_SEPARATOR)
        if mark == CURRENT_BRANCH_MARK:
            return commit, upstream
    return NO_CURRENT_BRANCH


def read_upstream_lag(run_process: Callable[[ProcessRequest], ProcessRecord], checkout: Path) -> UpstreamLag | None:
    branches = _read(run_process, checkout, "for-each-ref", BRANCH_FORMAT, "refs/heads")
    commit, upstream = _find_current_branch(branches)
    if not upstream:
        return None
    upstream_commit = _read(run_process, checkout, "rev-parse", "--short", "--verify", "--end-of-options", upstream)
    counts = _read(run_process, checkout, "rev-list", "--left-right", "--count", f"{upstream}...HEAD")
    behind = int(counts.split()[0])
    if behind == 0:
        return None
    return UpstreamLag(commit=commit, upstream=upstream, upstream_commit=upstream_commit.strip(), behind=behind)
