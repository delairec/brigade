from pathlib import Path

from brigade.git.delete_branch import delete_branch
from brigade.git.remove_worktree import remove_worktree
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime
from brigade.system.hold_lock import hold_lock
from brigade.system.locate_worktrees_lock import locate_worktrees_lock
from brigade.tick.actions import RemoveIntegrationBranch


def remove_integration_branch(runtime: Runtime, action: RemoveIntegrationBranch) -> None:
    repository = Path(read_project_field(find_project(read_projects(runtime), action.project), "PATH"))
    with hold_lock(locate_worktrees_lock(runtime.paths.lock_directory, action.project)):
        if action.worktree is not None:
            remove_worktree(runtime.run_process, repository, Path(action.worktree))
        delete_branch(runtime.run_process, repository, action.branch)
