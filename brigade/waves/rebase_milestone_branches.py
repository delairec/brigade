from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.git.check_ancestor import check_ancestor
from brigade.git.read_head import read_head
from brigade.ledger.milestone_rebased import MilestoneRebased
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.wave_started import WaveStarted
from brigade.registry.is_on_github import is_on_github
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.system.hold_lock import hold_lock
from brigade.system.locate_worktrees_lock import locate_worktrees_lock
from brigade.waves.branch_rebase_run import BranchRebaseRun
from brigade.waves.list_open_waves import list_open_waves
from brigade.waves.locate_forge_branch import locate_forge_branch
from brigade.waves.rebase_and_push_branch import rebase_and_push_branch
from brigade.waves.take_branch_worktree import take_branch_worktree

DESCENDING = 0
HEAD = "HEAD"
MAIN_FIELD = "MAIN"
NO_LOGIN = None


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


def _rebase_milestone(runtime: Runtime, rebase: MilestoneBranchesRebase, branch: str, main: str) -> MovedHead | None:
    worktree = take_branch_worktree(runtime, rebase, branch)
    if worktree is None:
        return None
    base = read_project_field(rebase.project, MAIN_FIELD)
    run = BranchRebaseRun(project=rebase.project.name, worktree=worktree.path, branch=branch, base=base, wave=None)
    before = rebase_and_push_branch(runtime, rebase, run, main)
    if before is None:
        return None
    after = read_head(runtime.run_process, worktree.path)
    if after == before:
        return None
    return MovedHead(before=before, after=after)


def _rebase_wave(runtime: Runtime, rebase: MilestoneBranchesRebase, wave: WaveStarted, milestone_branch: str) -> bool:
    worktree = take_branch_worktree(runtime, rebase, wave.branch)
    if worktree is None:
        return False
    if check_ancestor(runtime.run_process, worktree.path, milestone_branch, HEAD).exit_code == DESCENDING:
        return False
    run = BranchRebaseRun(
        project=rebase.project.name, worktree=worktree.path, branch=wave.branch, base=milestone_branch, wave=wave.wave
    )
    return rebase_and_push_branch(runtime, rebase, run, milestone_branch) is not None


def rebase_milestone_branches(runtime: Runtime, rebase: MilestoneBranchesRebase) -> MilestoneRebased | None:
    entries = read_ledger(runtime.paths.state_root).entries
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
