from pathlib import Path

LOCK_PREFIX = "worktrees-"
LOCK_SUFFIX = ".lock"


def locate_worktrees_lock(lock_directory: Path, project: str) -> Path:
    return lock_directory / f"{LOCK_PREFIX}{project}{LOCK_SUFFIX}"
