from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.git.list_local_branches import list_local_branches
from brigade.git.list_worktrees import Worktree, list_worktrees
from brigade.runs.is_run_live_on import is_run_live_on
from brigade.system.run_process import ProcessRecord, ProcessRequest

STALE_BRANCH = "stale branch"
MISSING_BRANCH = "missing branch"
DETACHED_WITHOUT_LIVE_RUN = "detached with no live run"


@dataclass(frozen=True)
class StaleWorktreesReading:
    repository: Path
    stale_branches: tuple[str, ...]
    state_root: Path
    is_alive: Callable[[Path], bool]


@dataclass(frozen=True)
class StaleWorktree:
    worktree: Worktree
    reason: str


def _find_reason(worktree: Worktree, local: tuple[str, ...], reading: StaleWorktreesReading) -> str | None:
    if worktree.branch in reading.stale_branches:
        return STALE_BRANCH
    if worktree.branch is not None and worktree.branch not in local:
        return MISSING_BRANCH
    if worktree.detached and not is_run_live_on(reading.state_root, worktree.path, reading.is_alive):
        return DETACHED_WITHOUT_LIVE_RUN
    return None


def read_stale_worktrees(
    run_process: Callable[[ProcessRequest], ProcessRecord], reading: StaleWorktreesReading
) -> tuple[StaleWorktree, ...]:
    _main_checkout, *linked = list_worktrees(run_process, reading.repository)
    local = list_local_branches(run_process, reading.repository)
    reasons = ((worktree, _find_reason(worktree, local, reading)) for worktree in linked)
    return tuple(StaleWorktree(worktree=worktree, reason=reason) for worktree, reason in reasons if reason is not None)
