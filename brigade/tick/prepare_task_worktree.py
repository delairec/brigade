import shlex
from pathlib import Path

from brigade.errors import BrigadeError, ToolFailure
from brigade.git.add_branch_worktree import BranchWorktree, add_branch_worktree
from brigade.git.delete_branch import delete_branch
from brigade.git.remove_worktree import remove_worktree
from brigade.git.require_ancestor import require_ancestor
from brigade.ledger.append_event import append_event
from brigade.ledger.task_state import TaskState
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime
from brigade.system.hold_lock import hold_lock
from brigade.system.locate_setup_log import locate_setup_log
from brigade.system.locate_worktrees_lock import locate_worktrees_lock
from brigade.system.read_configuration import Configuration
from brigade.system.run_process import ProcessRequest
from brigade.system.write_text_atomically import write_text_atomically
from brigade.tick.actions import LaunchTask
from brigade.tick.ignore_worktrees import ignore_worktrees

REPOSITORY_WORKTREE_ROOT = ".brigade/worktrees"
WAVE_BRANCH_PREFIX = "integration/"
TASK_BRANCH_PREFIX = "task/"
SETUP_FIELD = "SETUP"
SETUP_TIMEOUT_S = 1800.0
SETUP_PROMPT = "$ "
PARKED_STATE = "parked"


def _split_line(line: str) -> tuple[str, ...]:
    try:
        return tuple(shlex.split(line))
    except ValueError as error:
        raise ToolFailure(f"the line {line} splits into no argv: {error}") from None


def _set_up(runtime: Runtime, setup: tuple[str, ...], worktree: BranchWorktree, log: Path) -> None:
    transcript = []
    for line, argv in tuple((line, _split_line(line)) for line in setup):
        record = runtime.run_process(ProcessRequest(argv=argv, cwd=str(worktree.path), timeout_s=SETUP_TIMEOUT_S))
        transcript.append(f"{SETUP_PROMPT}{line}\n{record.stdout}{record.stderr}")
    write_text_atomically(log, "".join(transcript))
    require_ancestor(runtime.run_process, worktree.path, worktree.start)


def prepare_task_worktree(runtime: Runtime, configuration: Configuration, action: LaunchTask) -> BranchWorktree:
    project = find_project(read_projects(runtime), action.project)
    repository = Path(read_project_field(project, "PATH"))
    root = REPOSITORY_WORKTREE_ROOT if configuration.worktree_root is None else configuration.worktree_root
    worktree = BranchWorktree(
        path=repository / root / action.task,
        branch=f"{TASK_BRANCH_PREFIX}{action.branch.removeprefix(WAVE_BRANCH_PREFIX)}/{action.task}",
        start=action.branch,
    )
    lock = locate_worktrees_lock(runtime.paths.lock_directory, action.project)
    with hold_lock(lock):
        if configuration.worktree_root is None:
            ignore_worktrees(runtime.run_process, repository, action.branch)
        add_branch_worktree(runtime.run_process, repository, worktree)
    try:
        _set_up(
            runtime,
            tuple(field.value for field in project.fields if field.name == SETUP_FIELD),
            worktree,
            locate_setup_log(runtime.paths.setup_directory, action.project, action.task),
        )
    except ToolFailure as failure:
        with hold_lock(lock):
            remove_worktree(runtime.run_process, repository, worktree.path)
            delete_branch(runtime.run_process, repository, worktree.branch)
        append_event(runtime.paths, runtime.now, TaskState(wave=action.wave, task=action.task, state=PARKED_STATE))
        raise BrigadeError(f"the setup of @TASK.{action.task} failed: {failure}") from None
    return worktree
