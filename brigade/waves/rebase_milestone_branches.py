from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.git.add_branch_worktree import BranchWorktree
from brigade.git.add_worktree_on_branch import add_worktree_on_branch
from brigade.git.check_ancestor import check_ancestor
from brigade.git.list_worktrees import list_worktrees
from brigade.git.push_with_lease import LeasedPush, push_with_lease
from brigade.git.read_head import read_head
from brigade.git.rebase_onto import rebase_onto
from brigade.git.reset_worktree import reset_worktree
from brigade.ledger.milestone_rebased import MilestoneRebased
from brigade.ledger.wave_started import WaveStarted
from brigade.registry.is_on_github import is_on_github
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.system.hold_lock import hold_lock
from brigade.system.locate_worktrees_lock import locate_worktrees_lock
from brigade.system.parse_configuration import CLI_KEY
from brigade.waves.list_open_waves import list_open_waves
from brigade.waves.locate_branch_worktree import locate_branch_worktree
from brigade.waves.locate_forge_branch import locate_forge_branch

DESCENDING = 0
HEAD = "HEAD"
PATH_FIELD = "PATH"
MAIN_FIELD = "MAIN"
NO_LOGIN = None


@dataclass(frozen=True)
class BranchRebaseRun:
    project: str
    worktree: Path
    branch: str
    base: str
    wave: str | None


@dataclass(frozen=True)
class MovedHead:
    before: str
    after: str


@dataclass(frozen=True)
class MilestoneBranchesRebase:
    project: Entity
    milestone: str
    branch: str
    waves: tuple[str, ...]
    worktree_root: str | None
    read_environment: Callable[[str], dict]
    is_run_live_on: Callable[[Path], bool]
    launch_rebase_run: Callable[[BranchRebaseRun], None]
    read_login: Callable[[], str]


def _locate_branch_worktree(rebase: MilestoneBranchesRebase, branch: str) -> Path:
    repository = Path(read_project_field(rebase.project, PATH_FIELD))
    return locate_branch_worktree(repository, rebase.worktree_root, branch)


def _open_branch_worktree(runtime: Runtime, rebase: MilestoneBranchesRebase, worktree: BranchWorktree) -> None:
    repository = Path(read_project_field(rebase.project, PATH_FIELD))
    listed = list_worktrees(runtime.run_process, repository)
    if not any(found.path == worktree.path and found.branch == worktree.branch for found in listed):
        add_worktree_on_branch(runtime.run_process, repository, worktree)
    reset_worktree(runtime.run_process, worktree.path, worktree.start)


def _take_branch(runtime: Runtime, rebase: MilestoneBranchesRebase, branch: str) -> BranchWorktree | None:
    path = _locate_branch_worktree(rebase, branch)
    if rebase.is_run_live_on(path):
        return None
    start = locate_forge_branch(runtime.run_process, rebase.project, branch, rebase.read_environment)
    worktree = BranchWorktree(path=path, branch=branch, start=start)
    _open_branch_worktree(runtime, rebase, worktree)
    return worktree


def _rebase_branch(
    runtime: Runtime, rebase: MilestoneBranchesRebase, run: BranchRebaseRun, upstream: str
) -> str | None:
    head = read_head(runtime.run_process, run.worktree)
    if not rebase_onto(runtime.run_process, run.worktree, upstream):
        rebase.launch_rebase_run(run)
        return None
    if is_on_github(rebase.project):
        push = LeasedPush(
            worktree=run.worktree,
            branch=run.branch,
            expected_head=head,
            environment=rebase.read_environment(CLI_KEY),
        )
        push_with_lease(runtime.run_process, push)
    return head


def _rebase_milestone(runtime: Runtime, rebase: MilestoneBranchesRebase, branch: str, main: str) -> MovedHead | None:
    worktree = _take_branch(runtime, rebase, branch)
    if worktree is None:
        return None
    base = read_project_field(rebase.project, MAIN_FIELD)
    run = BranchRebaseRun(project=rebase.project.name, worktree=worktree.path, branch=branch, base=base, wave=None)
    before = _rebase_branch(runtime, rebase, run, main)
    if before is None:
        return None
    after = read_head(runtime.run_process, worktree.path)
    if after == before:
        return None
    return MovedHead(before=before, after=after)


def _rebase_wave(runtime: Runtime, rebase: MilestoneBranchesRebase, wave: WaveStarted, milestone_branch: str) -> bool:
    worktree = _take_branch(runtime, rebase, wave.branch)
    if worktree is None:
        return False
    if check_ancestor(runtime.run_process, worktree.path, milestone_branch, HEAD).exit_code == DESCENDING:
        return False
    run = BranchRebaseRun(
        project=rebase.project.name, worktree=worktree.path, branch=wave.branch, base=milestone_branch, wave=wave.wave
    )
    return _rebase_branch(runtime, rebase, run, milestone_branch) is not None


def rebase_milestone_branches(runtime: Runtime, rebase: MilestoneBranchesRebase) -> MilestoneRebased | None:
    entries = runtime.read_ledger(runtime.paths.state_root).entries
    project = rebase.project.name
    with hold_lock(locate_worktrees_lock(runtime.paths.lock_directory, project)):
        main_branch = read_project_field(rebase.project, MAIN_FIELD)
        main = locate_forge_branch(runtime.run_process, rebase.project, main_branch, rebase.read_environment)
        login = rebase.read_login() if is_on_github(rebase.project) else NO_LOGIN
        moved = _rebase_milestone(runtime, rebase, rebase.branch, main)
        rebased_waves = tuple(
            wave.wave
            for wave in list_open_waves(entries, project)
            if wave.wave in rebase.waves and _rebase_wave(runtime, rebase, wave, rebase.branch)
        )
    if moved is None:
        return None
    return MilestoneRebased(
        project=project,
        milestone=rebase.milestone,
        branch=rebase.branch,
        before=moved.before,
        after=moved.after,
        waves=rebased_waves,
        login=login,
    )
