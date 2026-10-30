from pathlib import Path

from brigade.tick.locate_scheduled_worktree import locate_scheduled_worktree

BRANCH_SEPARATOR = "/"
WORKTREE_SEPARATOR = "-"


def locate_branch_worktree(repository: Path, worktree_root: str | None, branch: str) -> Path:
    return locate_scheduled_worktree(repository, worktree_root, branch.replace(BRANCH_SEPARATOR, WORKTREE_SEPARATOR))
