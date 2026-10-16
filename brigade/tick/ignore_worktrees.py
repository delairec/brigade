from collections.abc import Callable
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.git.commit_root_file_on_branch import RootFileCommit, commit_root_file_on_branch
from brigade.git.list_worktrees import list_worktrees
from brigade.git.read_file_at import read_file_at
from brigade.system.run_process import ProcessRecord, ProcessRequest

IGNORE_FILE = ".gitignore"
IGNORED_DIRECTORY = ".brigade/worktrees/"
COMMIT_MESSAGE = f"brigade tick: ignore {IGNORED_DIRECTORY}"


def ignore_worktrees(run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, branch: str) -> None:
    ignored = read_file_at(run_process, repository, f"{branch}:{IGNORE_FILE}").splitlines()
    if IGNORED_DIRECTORY in ignored:
        return
    checkout = next(
        (worktree for worktree in list_worktrees(run_process, repository) if worktree.branch == branch), None
    )
    if checkout is not None:
        raise BrigadeError(f"the wave branch {branch} is checked out in {checkout.path}")
    commit_root_file_on_branch(
        run_process,
        repository,
        RootFileCommit(
            branch=branch,
            path=IGNORE_FILE,
            content="".join(f"{line}\n" for line in (*ignored, IGNORED_DIRECTORY)),
            message=COMMIT_MESSAGE,
        ),
    )
