import shlex
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.errors import BrigadeError, ToolFailure
from brigade.git.add_branch_worktree import BranchWorktree, add_branch_worktree
from brigade.git.add_worktree_on_branch import add_worktree_on_branch
from brigade.git.check_ancestor import check_ancestor
from brigade.git.commit_files import CommitRequest, commit_files
from brigade.git.find_branch import find_branch
from brigade.git.list_worktrees import list_worktrees
from brigade.git.rebase_onto import rebase_onto
from brigade.git.require_ancestor import require_ancestor
from brigade.git.switch_worktree_to_branch import switch_worktree_to_branch
from brigade.git.switch_worktree_to_new_branch import switch_worktree_to_new_branch
from brigade.ledger.append_event import append_event
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.task_state import TaskState
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime
from brigade.system.hold_lock import hold_lock
from brigade.system.locate_setup_log import locate_setup_log
from brigade.system.locate_worktrees_lock import locate_worktrees_lock
from brigade.system.parse_configuration import Configuration
from brigade.system.run_process import ProcessRequest
from brigade.system.write_text_atomically import write_text_atomically
from brigade.tick.actions import LaunchTask
from brigade.tick.ignore_worktrees import ignore_worktrees
from brigade.tick.locate_scheduled_worktree import locate_scheduled_worktree
from brigade.tick.name_cancelled_task_branches import name_cancelled_task_branches
from brigade.tick.name_task_branch import name_task_branch
from brigade.waves.locate_forge_branch import locate_forge_branch
from brigade.waves.read_task_state import PARKED_STATE

SETUP_FIELD = "SETUP"
SETUP_TIMEOUT_S = 1800.0
SETUP_PROMPT = "$ "
SETUP_FAILED_REASON = "setup failed"
DESCENDING = 0
WHOLE_WORKTREE = "."


@dataclass(frozen=True)
class PreparedWorktree:
    worktree: BranchWorktree
    conflicted: bool


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


def _keep_uncommitted_changes(runtime: Runtime, worktree: BranchWorktree, task: str) -> None:
    commit_files(
        runtime.run_process,
        CommitRequest(
            repository=worktree.path,
            files=(WHOLE_WORKTREE,),
            message=f"brigade tick: keep the changes of @TASK.{task} left uncommitted in a cancelled wave",
        ),
    )


def _open_worktree(runtime: Runtime, repository: Path, worktree: BranchWorktree, action: LaunchTask) -> bool:
    listed = list_worktrees(runtime.run_process, repository)
    held = next((found.branch for found in listed if found.path == worktree.path), None)
    if held == worktree.branch:
        return True
    found = find_branch(runtime.run_process, repository, worktree.branch)
    cancelled = name_cancelled_task_branches(read_ledger(runtime.paths.state_root).entries, action.project, action.task)
    if held in cancelled:
        _keep_uncommitted_changes(runtime, worktree, action.task)
        (switch_worktree_to_branch if found else switch_worktree_to_new_branch)(runtime.run_process, worktree)
    elif found:
        add_worktree_on_branch(runtime.run_process, repository, worktree)
    else:
        add_branch_worktree(runtime.run_process, repository, worktree)
    return found


def _put_on_start(runtime: Runtime, worktree: BranchWorktree) -> bool:
    descent = check_ancestor(runtime.run_process, worktree.path, worktree.start, worktree.branch)
    return descent.exit_code == DESCENDING or rebase_onto(runtime.run_process, worktree.path, worktree.start)


def _set_up_or_park(runtime: Runtime, project: Entity, action: LaunchTask, worktree: BranchWorktree) -> None:
    try:
        _set_up(
            runtime,
            tuple(field.value for field in project.fields if field.name == SETUP_FIELD),
            worktree,
            locate_setup_log(runtime.paths.setup_directory, action.project, action.task),
        )
    except ToolFailure as failure:
        append_event(
            runtime.paths,
            runtime.now,
            TaskState(wave=action.wave, task=action.task, state=PARKED_STATE, reason=SETUP_FAILED_REASON),
        )
        raise BrigadeError(f"the setup of @TASK.{action.task} failed: {failure}") from None


def prepare_task_worktree(
    runtime: Runtime, configuration: Configuration, action: LaunchTask, read_environment: Callable[[str], dict]
) -> PreparedWorktree:
    project = find_project(read_projects(runtime), action.project)
    repository = Path(read_project_field(project, "PATH"))
    lock = locate_worktrees_lock(runtime.paths.lock_directory, action.project)
    with hold_lock(lock):
        worktree = BranchWorktree(
            path=locate_scheduled_worktree(repository, configuration.worktree_root, action.task),
            branch=name_task_branch(action.branch, action.task),
            start=locate_forge_branch(runtime.run_process, project, action.branch, read_environment),
        )
        if configuration.worktree_root is None:
            ignore_worktrees(runtime.run_process, repository, action.branch)
        if _open_worktree(runtime, repository, worktree, action) and not _put_on_start(runtime, worktree):
            return PreparedWorktree(worktree=worktree, conflicted=True)
    _set_up_or_park(runtime, project, action, worktree)
    return PreparedWorktree(worktree=worktree, conflicted=False)
