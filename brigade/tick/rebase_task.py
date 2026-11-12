from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.git.commit_files import CommitRequest, commit_files
from brigade.git.fetch_branches import REMOTE, BranchesFetch, fetch_branches
from brigade.git.push_with_lease import LeasedPush, push_with_lease
from brigade.git.read_head import read_head
from brigade.git.rebase_onto import rebase_onto
from brigade.registry.find_project import find_project
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime
from brigade.system.hold_lock import hold_lock
from brigade.system.locate_worktrees_lock import locate_worktrees_lock
from brigade.tick.actions import RebaseTask
from brigade.tick.head_proof import GREEN, HeadProof, HoldingHead
from brigade.tick.prove_branch_head import BranchHead, prove_branch_head

WHOLE_WORKTREE = "."


@dataclass(frozen=True)
class TaskRebase:
    head: str | None
    held_by: HoldingHead | None = None


def _prove_base_head(
    runtime: Runtime, action: RebaseTask, worktree: Path, list_check_runs: Callable[[str, str], list[dict]]
) -> HeadProof:
    return prove_branch_head(
        runtime,
        BranchHead(
            project=find_project(read_projects(runtime), action.project),
            repository=worktree,
            branch=action.branch,
            ref=f"{REMOTE}/{action.branch}",
            list_check_runs=list_check_runs,
        ),
    )


def _keep_uncommitted_changes(runtime: Runtime, action: RebaseTask, worktree: Path) -> None:
    commit_files(
        runtime.run_process,
        CommitRequest(
            repository=worktree,
            files=(WHOLE_WORKTREE,),
            message=f"chore(tick): keep the changes of @TASK.{action.task} left uncommitted before its rebase",
        ),
    )


def rebase_task(
    runtime: Runtime, action: RebaseTask, environment: dict, list_check_runs: Callable[[str, str], list[dict]]
) -> TaskRebase:
    worktree = Path(action.worktree)
    with hold_lock(locate_worktrees_lock(runtime.paths.lock_directory, action.project)):
        if action.holds_uncommitted_changes:
            _keep_uncommitted_changes(runtime, action, worktree)
        fetch_branches(
            runtime.run_process, BranchesFetch(repository=worktree, branches=(action.branch,), environment=environment)
        )
        base_head = _prove_base_head(runtime, action, worktree, list_check_runs)
        if base_head.state != GREEN:
            return TaskRebase(head=None, held_by=HoldingHead(branch=action.branch, proof=base_head))
        if not rebase_onto(runtime.run_process, worktree, f"{REMOTE}/{action.branch}"):
            return TaskRebase(head=None)
        push_with_lease(
            runtime.run_process,
            LeasedPush(
                worktree=worktree,
                branch=action.task_branch,
                expected_head=action.head,
                environment=environment,
            ),
        )
        return TaskRebase(head=read_head(runtime.run_process, worktree))
