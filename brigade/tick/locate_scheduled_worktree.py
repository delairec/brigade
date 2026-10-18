from pathlib import Path

REPOSITORY_WORKTREE_ROOT = ".brigade/worktrees"


def locate_scheduled_worktree(repository: Path, worktree_root: str | None, task: str) -> Path:
    return repository / (REPOSITORY_WORKTREE_ROOT if worktree_root is None else worktree_root) / task
