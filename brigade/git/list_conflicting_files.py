from collections.abc import Callable
from pathlib import Path

from brigade.git.timeouts import TREE_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest

CLEAN_OR_CONFLICTING = (0, 1)


def list_conflicting_files(
    run_process: Callable[[ProcessRequest], ProcessRecord], worktree: Path, upstream: str
) -> list[str]:
    merged = run_process(
        ProcessRequest(
            argv=("git", "merge-tree", "--write-tree", "--name-only", "--no-messages", "HEAD", upstream),
            cwd=str(worktree),
            timeout_s=TREE_TIMEOUT_S,
            acceptable_exit_codes=CLEAN_OR_CONFLICTING,
        )
    )
    return merged.stdout.splitlines()[1:]
