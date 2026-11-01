from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.errors import BrigadeError
from brigade.git.cut_branch import BranchCut, cut_branch
from brigade.git.delete_branch import delete_branch
from brigade.git.find_branch import find_branch
from brigade.git.find_remote_branch import RemoteBranch, find_remote_branch
from brigade.git.push_branch import BranchPush, push_branch
from brigade.git.push_ref_to_branch import RefPush, push_ref_to_branch
from brigade.ledger.append_event import append_event
from brigade.ledger.milestone_branch_cut import MilestoneBranchCut
from brigade.registry.is_on_github import is_on_github
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.system.hold_lock import hold_lock
from brigade.system.locate_worktrees_lock import locate_worktrees_lock
from brigade.system.parse_configuration import CLI_KEY
from brigade.waves.find_milestone_branch import find_milestone_branch
from brigade.waves.is_milestone_branch_off_the_forge import RecordedMilestoneBranch, is_milestone_branch_off_the_forge
from brigade.waves.locate_project_main import locate_project_main
from brigade.waves.name_milestone_branch import name_milestone_branch

NO_LOGIN = None


@dataclass(frozen=True)
class MilestoneBranchDemand:
    project: Entity
    milestone: Entity
    read_environment: Callable[[str], dict]
    read_login: Callable[[], str]


def _find_owner(entries: tuple, project: str, branch: str) -> str | None:
    return next(
        (
            entry.event.milestone
            for entry in reversed(entries)
            if isinstance(entry.event, MilestoneBranchCut)
            and entry.event.project == project
            and entry.event.branch == branch
        ),
        None,
    )


def _find_branch_anywhere(runtime: Runtime, demand: MilestoneBranchDemand, branch: str) -> bool:
    repository = Path(read_project_field(demand.project, "PATH"))
    if find_branch(runtime.run_process, repository, branch):
        return True
    if not is_on_github(demand.project):
        return False
    remote_branch = RemoteBranch(repository=repository, branch=branch, environment=demand.read_environment(CLI_KEY))
    return find_remote_branch(runtime.run_process, remote_branch)


def _cut_and_record(runtime: Runtime, demand: MilestoneBranchDemand, branch: str) -> None:
    repository = Path(read_project_field(demand.project, "PATH"))
    start = locate_project_main(runtime.run_process, demand.project, demand.read_environment)
    login = demand.read_login() if is_on_github(demand.project) else NO_LOGIN
    cut_branch(runtime.run_process, BranchCut(repository=repository, branch=branch, start=start))
    if is_on_github(demand.project):
        push = BranchPush(repository=repository, branch=branch, environment=demand.read_environment(CLI_KEY))
        try:
            push_branch(runtime.run_process, push)
        except BrigadeError:
            delete_branch(runtime.run_process, repository, branch)
            raise
    cut = MilestoneBranchCut(project=demand.project.name, milestone=demand.milestone.name, branch=branch, login=login)
    append_event(runtime.paths, runtime.now, cut)


def _cut_again_and_record(runtime: Runtime, demand: MilestoneBranchDemand, branch: str) -> None:
    start = locate_project_main(runtime.run_process, demand.project, demand.read_environment)
    login = demand.read_login()
    push = RefPush(
        repository=Path(read_project_field(demand.project, "PATH")),
        ref=start,
        branch=branch,
        environment=demand.read_environment(CLI_KEY),
    )
    push_ref_to_branch(runtime.run_process, push)
    cut = MilestoneBranchCut(project=demand.project.name, milestone=demand.milestone.name, branch=branch, login=login)
    append_event(runtime.paths, runtime.now, cut)


def cut_milestone_branch(runtime: Runtime, demand: MilestoneBranchDemand) -> str:
    with hold_lock(locate_worktrees_lock(runtime.paths.lock_directory, demand.project.name)):
        entries = runtime.read_ledger(runtime.paths.state_root).entries
        recorded = find_milestone_branch(entries, demand.project.name, demand.milestone.name)
        if recorded is not None:
            recorded_branch = RecordedMilestoneBranch(
                project=demand.project, branch=recorded, read_environment=demand.read_environment
            )
            if is_milestone_branch_off_the_forge(runtime.run_process, recorded_branch):
                _cut_again_and_record(runtime, demand, recorded)
            return recorded
        branch = name_milestone_branch(read_project_field(demand.milestone, "TITLE"))
        owner = _find_owner(entries, demand.project.name, branch)
        if owner is not None:
            raise BrigadeError(
                f"@MILESTONE.{demand.milestone.name}: the branch {branch} is the branch of @MILESTONE.{owner}"
            )
        if _find_branch_anywhere(runtime, demand, branch):
            raise BrigadeError(
                f"@MILESTONE.{demand.milestone.name}: the branch {branch} exists and no milestone.branch_cut records it"
            )
        _cut_and_record(runtime, demand, branch)
        return branch
