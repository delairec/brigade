from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.git.timeouts import TREE_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest


@dataclass(frozen=True)
class DetachedWorktree:
    repository: Path
    path: Path
    start: str
    reason: str


def add_detached_worktree(run_process: Callable[[ProcessRequest], ProcessRecord], worktree: DetachedWorktree) -> None:
    run_process(
        ProcessRequest(
            argv=(
                "git",
                "worktree",
                "add",
                "--quiet",
                "--detach",
                "--lock",
                "--reason",
                worktree.reason,
                str(worktree.path),
                worktree.start,
            ),
            cwd=str(worktree.repository),
            timeout_s=TREE_TIMEOUT_S,
        )
    )
