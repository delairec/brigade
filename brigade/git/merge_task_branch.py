from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.git.add_branch_worktree import BranchWorktree
from brigade.git.open_branch_worktree import open_branch_worktree
from brigade.git.timeouts import TREE_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest

SQUASH_METHOD = "squash"
MERGE_OPTIONS_BY_METHOD = {"merge": ("--no-ff",), "rebase": ()}
MERGED_OR_CONFLICTED = (0, 1)
MERGED = 0


@dataclass(frozen=True)
class TaskBranchMerge:
    repository: Path
    worktree: Path
    branch: str
    head: str
    method: str
    message: str


def _run_git(
    run_process: Callable[[ProcessRequest], ProcessRecord],
    merge: TaskBranchMerge,
    *arguments: str,
    acceptable_exit_codes: tuple[int, ...] = (0,),
) -> ProcessRecord:
    return run_process(
        ProcessRequest(
            argv=("git", *arguments),
            cwd=str(merge.worktree),
            timeout_s=TREE_TIMEOUT_S,
            acceptable_exit_codes=acceptable_exit_codes,
        )
    )


def _squash(run_process: Callable[[ProcessRequest], ProcessRecord], merge: TaskBranchMerge) -> bool:
    squashed = _run_git(
        run_process, merge, "merge", "--quiet", "--squash", merge.head, acceptable_exit_codes=MERGED_OR_CONFLICTED
    )
    if squashed.exit_code != MERGED:
        return False
    _run_git(run_process, merge, "commit", "--quiet", "-m", merge.message)
    return True


def _merge(run_process: Callable[[ProcessRequest], ProcessRecord], merge: TaskBranchMerge) -> bool:
    merged = _run_git(
        run_process,
        merge,
        "merge",
        "--quiet",
        *MERGE_OPTIONS_BY_METHOD[merge.method],
        "-m",
        merge.message,
        merge.head,
        acceptable_exit_codes=MERGED_OR_CONFLICTED,
    )
    return merged.exit_code == MERGED


def merge_task_branch(run_process: Callable[[ProcessRequest], ProcessRecord], merge: TaskBranchMerge) -> bool:
    open_branch_worktree(
        run_process, merge.repository, BranchWorktree(path=merge.worktree, branch=merge.branch, start=merge.branch)
    )
    merged = _squash(run_process, merge) if merge.method == SQUASH_METHOD else _merge(run_process, merge)
    if not merged:
        _run_git(run_process, merge, "reset", "--quiet", "--merge")
    return merged
