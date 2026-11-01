from pathlib import Path

from brigade.git.add_branch_worktree import BranchWorktree
from brigade.git.add_worktree_on_branch import add_worktree_on_branch
from brigade.git.list_worktrees import list_worktrees
from brigade.git.reset_worktree import reset_worktree
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.waves.branch_rebase_run import BranchRebaseGateways
from brigade.waves.locate_branch_worktree import locate_branch_worktree
from brigade.waves.locate_forge_branch import locate_forge_branch

PATH_FIELD = "PATH"


def _open_branch_worktree(runtime: Runtime, repository: Path, worktree: BranchWorktree) -> None:
    listed = list_worktrees(runtime.run_process, repository)
    if not any(found.path == worktree.path and found.branch == worktree.branch for found in listed):
        add_worktree_on_branch(runtime.run_process, repository, worktree)
    reset_worktree(runtime.run_process, worktree.path, worktree.start)


def take_branch_worktree(runtime: Runtime, gateways: BranchRebaseGateways, branch: str) -> BranchWorktree | None:
    repository = Path(read_project_field(gateways.project, PATH_FIELD))
    path = locate_branch_worktree(repository, gateways.worktree_root, branch)
    if gateways.is_run_live_on(path):
        return None
    start = locate_forge_branch(runtime.run_process, gateways.project, branch, gateways.read_environment)
    worktree = BranchWorktree(path=path, branch=branch, start=start)
    _open_branch_worktree(runtime, repository, worktree)
    return worktree
