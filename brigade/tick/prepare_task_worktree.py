import shlex
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.errors import BrigadeError, ToolFailure
from brigade.git.add_branch_worktree import BranchWorktree, add_branch_worktree
from brigade.git.add_worktree_on_branch import add_worktree_on_branch
from brigade.git.check_ancestor import check_ancestor
from brigade.git.find_branch import find_branch
from brigade.git.list_worktrees import list_worktrees
from brigade.git.read_head import read_head
from brigade.git.rebase_onto import rebase_onto
from brigade.git.require_ancestor import require_ancestor
from brigade.git.resolve_commit import resolve_commit
from brigade.ledger.append_event import append_event
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
from brigade.tick.head_proof import GREEN, RED, ForgeCheck, HeadProof
from brigade.tick.ignore_worktrees import ignore_worktrees
from brigade.tick.locate_scheduled_worktree import locate_scheduled_worktree
from brigade.tick.prove_head import HeadQuery, prove_head
from brigade.tick.read_task_check import read_task_check
from brigade.waves.locate_forge_branch import locate_forge_branch
from brigade.waves.read_task_state import PARKED_STATE

SETUP_FIELD = "SETUP"
MAIN_FIELD = "MAIN"
SETUP_TIMEOUT_S = 1800.0
SETUP_PROMPT = "$ "
SETUP_FAILED_REASON = "setup failed"
DESCENDING = 0
WHOLE_WORKTREE = "."
NO_TASK_CHECK = None
NO_FORGE_CHECK = ()


@dataclass(frozen=True)
class PreparedWorktree:
    worktree: BranchWorktree
    conflicted: bool
    on_start: bool
    rebased: bool = False
    failed_commands: tuple[str, ...] = ()


def _split_line(line: str) -> tuple[str, ...]:
    try:
        return tuple(shlex.split(line))
    except ValueError as error:
        raise ToolFailure(f"the line {line} splits into no argv: {error}") from None


def _set_up(runtime: Runtime, setup: tuple[str, ...], prepared: PreparedWorktree, log: Path) -> None:
    worktree = prepared.worktree
    transcript = []
    for line, argv in tuple((line, _split_line(line)) for line in setup):
        record = runtime.run_process(ProcessRequest(argv=argv, cwd=str(worktree.path), timeout_s=SETUP_TIMEOUT_S))
        transcript.append(f"{SETUP_PROMPT}{line}\n{record.stdout}{record.stderr}")
    write_text_atomically(log, "".join(transcript))
    if prepared.on_start:
        require_ancestor(runtime.run_process, worktree.path, worktree.start)


def _open_worktree(runtime: Runtime, repository: Path, worktree: BranchWorktree) -> bool:
    listed = list_worktrees(runtime.run_process, repository)
    held = next((found.branch for found in listed if found.path == worktree.path), None)
    if held == worktree.branch:
        return True
    found = find_branch(runtime.run_process, repository, worktree.branch)
    if found:
        add_worktree_on_branch(runtime.run_process, repository, worktree)
    else:
        add_branch_worktree(runtime.run_process, repository, worktree)
    return found


@dataclass(frozen=True)
class _Launch:
    project: Entity
    repository: Path
    worktree: BranchWorktree
    action: LaunchTask


def _read_pull_request_checks(action: LaunchTask, commit: str) -> tuple[ForgeCheck, ...]:
    checked = action.pull_request_checks
    if checked is None or checked.head != commit:
        return NO_FORGE_CHECK
    return checked.checks


def _prove_task_head(runtime: Runtime, launch: _Launch) -> HeadProof:
    commit = read_head(runtime.run_process, launch.worktree.path)
    return prove_head(
        runtime,
        HeadQuery(
            project=launch.project,
            repository=launch.repository,
            commit=commit,
            task_check=read_task_check(runtime.paths.state_root, launch.project.name, launch.action.task),
            forge_checks=_read_pull_request_checks(launch.action, commit),
        ),
    )


def _prove_start_head(runtime: Runtime, launch: _Launch) -> HeadProof:
    return prove_head(
        runtime,
        HeadQuery(
            project=launch.project,
            repository=launch.repository,
            commit=resolve_commit(runtime.run_process, launch.worktree.path, launch.worktree.start),
            task_check=NO_TASK_CHECK,
            forge_checks=NO_FORGE_CHECK,
        ),
    )


def _put_on_start(runtime: Runtime, launch: _Launch) -> PreparedWorktree:
    worktree = launch.worktree
    descent = check_ancestor(runtime.run_process, worktree.path, worktree.start, worktree.branch)
    if descent.exit_code == DESCENDING:
        return PreparedWorktree(worktree=worktree, conflicted=False, on_start=True)
    task_head = _prove_task_head(runtime, launch)
    if task_head.state == RED:
        return PreparedWorktree(
            worktree=worktree, conflicted=False, on_start=False, failed_commands=task_head.failed_commands
        )
    if task_head.state != GREEN or _prove_start_head(runtime, launch).state != GREEN:
        return PreparedWorktree(worktree=worktree, conflicted=False, on_start=False)
    rebased = rebase_onto(runtime.run_process, worktree.path, worktree.start)
    return PreparedWorktree(worktree=worktree, conflicted=not rebased, on_start=rebased, rebased=rebased)


def _set_up_or_park(runtime: Runtime, project: Entity, action: LaunchTask, prepared: PreparedWorktree) -> None:
    try:
        _set_up(
            runtime,
            tuple(field.value for field in project.fields if field.name == SETUP_FIELD),
            prepared,
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
            branch=action.task_branch,
            start=locate_forge_branch(runtime.run_process, project, action.branch, read_environment),
        )
        if configuration.worktree_root is None and action.branch != read_project_field(project, MAIN_FIELD):
            ignore_worktrees(runtime.run_process, repository, action.branch)
        prepared = (
            _put_on_start(runtime, _Launch(project=project, repository=repository, worktree=worktree, action=action))
            if _open_worktree(runtime, repository, worktree)
            else PreparedWorktree(worktree=worktree, conflicted=False, on_start=True)
        )
        if prepared.conflicted:
            return prepared
    _set_up_or_park(runtime, project, action, prepared)
    return prepared
