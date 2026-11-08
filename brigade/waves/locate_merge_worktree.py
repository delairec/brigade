from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.git.list_worktrees import list_worktrees
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.waves.locate_branch_worktree import locate_branch_worktree


@dataclass(frozen=True)
class MergeWorktree:
    path: Path
    opened: bool


def locate_merge_worktree(
    run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, worktree_root: str | None, branch: str
) -> MergeWorktree:
    holding = next(
        (worktree for worktree in list_worktrees(run_process, repository) if worktree.branch == branch), None
    )
    if holding is None:
        return MergeWorktree(path=locate_branch_worktree(repository, worktree_root, branch), opened=False)
    return MergeWorktree(path=holding.path, opened=True)
