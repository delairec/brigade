from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.git.read_head import read_head
from brigade.ledger.wave_rebased import WaveRebased
from brigade.registry.is_on_github import is_on_github
from brigade.runtime import Runtime
from brigade.system.hold_lock import hold_lock
from brigade.system.locate_worktrees_lock import locate_worktrees_lock
from brigade.waves.branch_rebase_run import BranchRebaseRun
from brigade.waves.locate_forge_branch import locate_forge_branch
from brigade.waves.rebase_and_push_branch import rebase_and_push_branch
from brigade.waves.take_branch_worktree import take_branch_worktree

NO_LOGIN = None


@dataclass(frozen=True)
class WaveBranchRebase:
    project: Entity
    wave: str
    branch: str
    base: str
    worktree_root: str | None
    read_environment: Callable[[str], dict]
    is_run_live_on: Callable[[Path], bool]
    launch_rebase_run: Callable[[BranchRebaseRun], None]
    read_login: Callable[[], str]


def rebase_wave_branch(runtime: Runtime, rebase: WaveBranchRebase) -> WaveRebased | None:
    project = rebase.project.name
    with hold_lock(locate_worktrees_lock(runtime.paths.lock_directory, project)):
        login = rebase.read_login() if is_on_github(rebase.project) else NO_LOGIN
        worktree = take_branch_worktree(runtime, rebase, rebase.branch)
        if worktree is None:
            return None
        upstream = locate_forge_branch(runtime.run_process, rebase.project, rebase.base, rebase.read_environment)
        run = BranchRebaseRun(
            project=project, worktree=worktree.path, branch=rebase.branch, base=rebase.base, wave=rebase.wave
        )
        before = rebase_and_push_branch(runtime, rebase, run, upstream)
        if before is None:
            return None
        after = read_head(runtime.run_process, worktree.path)
    if after == before:
        return None
    return WaveRebased(project=project, wave=rebase.wave, branch=rebase.branch, before=before, after=after, login=login)
