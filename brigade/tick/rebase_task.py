from pathlib import Path

from brigade.git.commit_files import CommitRequest, commit_files
from brigade.git.fetch_branches import REMOTE, BranchesFetch, fetch_branches
from brigade.git.push_with_lease import LeasedPush, push_with_lease
from brigade.git.read_head import read_head
from brigade.git.rebase_onto import rebase_onto
from brigade.runtime import Runtime
from brigade.system.hold_lock import hold_lock
from brigade.system.locate_worktrees_lock import locate_worktrees_lock
from brigade.tick.actions import RebaseTask
from brigade.tick.name_task_branch import name_task_branch

WHOLE_WORKTREE = "."


def rebase_task(runtime: Runtime, action: RebaseTask, environment: dict) -> str | None:
    worktree = Path(action.worktree)
    with hold_lock(locate_worktrees_lock(runtime.paths.lock_directory, action.project)):
        if action.holds_uncommitted_changes:
            commit_files(
                runtime.run_process,
                CommitRequest(
                    repository=worktree,
                    files=(WHOLE_WORKTREE,),
                    message=f"chore(tick): keep the changes of @TASK.{action.task} left uncommitted before its rebase",
                ),
            )
        fetch_branches(
            runtime.run_process, BranchesFetch(repository=worktree, branches=(action.branch,), environment=environment)
        )
        if not rebase_onto(runtime.run_process, worktree, f"{REMOTE}/{action.branch}"):
            return None
        push_with_lease(
            runtime.run_process,
            LeasedPush(
                worktree=worktree,
                branch=name_task_branch(action.branch, action.task),
                expected_head=action.head,
                environment=environment,
            ),
        )
        return read_head(runtime.run_process, worktree)
