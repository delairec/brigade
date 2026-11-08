from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.git.add_branch_worktree import BranchWorktree
from brigade.git.add_worktree_on_branch import add_worktree_on_branch
from brigade.git.list_worktrees import list_worktrees
from brigade.git.push_with_lease import LeasedPush, push_with_lease
from brigade.git.read_head import read_head
from brigade.git.rebase_onto import rebase_onto
from brigade.git.reset_worktree import reset_worktree
from brigade.git.resolve_commit import resolve_commit
from brigade.ledger.milestone_rebase_launched import MilestoneRebaseLaunched
from brigade.ledger.milestone_rebased import MilestoneRebased
from brigade.registry.is_on_github import is_on_github
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.system.hold_lock import hold_lock
from brigade.system.locate_worktrees_lock import locate_worktrees_lock
from brigade.system.parse_configuration import CLI_KEY
from brigade.tick.head_proof import GREEN, HoldingHead
from brigade.tick.prove_branch_head import BranchHead, prove_branch_head
from brigade.tick.run_commit_checks import run_commit_checks
from brigade.waves.locate_branch_worktree import locate_branch_worktree
from brigade.waves.locate_forge_branch import locate_forge_branch

PATH_FIELD = "PATH"
MAIN_FIELD = "MAIN"
PASSED_EXIT_CODE = 0
NO_LOGIN = None
NO_WAVE_REBASED = ()


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
class LaunchedRun:
    run: str
    main_head: str | None
    branch_head: str


@dataclass(frozen=True)
class MilestoneBranchesRebase:
    project: Entity
    milestone: str
    branch: str
    worktree_root: str | None
    read_environment: Callable[[str], dict]
    is_run_live_on: Callable[[Path], bool]
    launch_rebase_run: Callable[[BranchRebaseRun], str]
    read_login: Callable[[], str]
    name_holding_head: Callable[[HoldingHead], None]
    list_check_runs: Callable[[str, str], list[dict]]


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


def _read_rebased_head(runtime: Runtime, worktree: Path, upstream: str) -> str | None:
    if not rebase_onto(runtime.run_process, worktree, upstream):
        return None
    return read_head(runtime.run_process, worktree)


def _push_branch(runtime: Runtime, rebase: MilestoneBranchesRebase, run: BranchRebaseRun, head: str) -> None:
    if is_on_github(rebase.project):
        push = LeasedPush(
            worktree=run.worktree,
            branch=run.branch,
            expected_head=head,
            environment=rebase.read_environment(CLI_KEY),
        )
        push_with_lease(runtime.run_process, push)


def _pass_project_checks(runtime: Runtime, rebase: MilestoneBranchesRebase, worktree: Path, head: str) -> bool:
    checks = run_commit_checks(runtime, rebase.project, worktree, head)
    return all(result.exit_code == PASSED_EXIT_CODE for result in checks.results)


def _find_holding_head(
    runtime: Runtime, rebase: MilestoneBranchesRebase, worktree: BranchWorktree, main: str
) -> HoldingHead | None:
    for branch, ref in ((read_project_field(rebase.project, MAIN_FIELD), main), (worktree.branch, worktree.start)):
        proof = prove_branch_head(
            runtime,
            BranchHead(
                project=rebase.project,
                repository=worktree.path,
                branch=branch,
                ref=ref,
                list_check_runs=rebase.list_check_runs,
            ),
        )
        if proof.state != GREEN:
            return HoldingHead(branch=branch, proof=proof)
    return None


def _rebase_milestone(
    runtime: Runtime, rebase: MilestoneBranchesRebase, branch: str, main: str
) -> MovedHead | LaunchedRun | None:
    worktree = _take_branch(runtime, rebase, branch)
    if worktree is None:
        return None
    held_by = _find_holding_head(runtime, rebase, worktree, main)
    if held_by is not None:
        rebase.name_holding_head(held_by)
        return None
    base = read_project_field(rebase.project, MAIN_FIELD)
    run = BranchRebaseRun(project=rebase.project.name, worktree=worktree.path, branch=branch, base=base, wave=None)
    before = read_head(runtime.run_process, worktree.path)
    after = _read_rebased_head(runtime, worktree.path, main)
    if after is None or (after != before and not _pass_project_checks(runtime, rebase, worktree.path, after)):
        return LaunchedRun(
            run=rebase.launch_rebase_run(run),
            main_head=resolve_commit(runtime.run_process, worktree.path, main),
            branch_head=before,
        )
    _push_branch(runtime, rebase, run, before)
    if after == before:
        return None
    return MovedHead(before=before, after=after)


def rebase_milestone_branches(
    runtime: Runtime, rebase: MilestoneBranchesRebase
) -> MilestoneRebased | MilestoneRebaseLaunched | None:
    project = rebase.project.name
    with hold_lock(locate_worktrees_lock(runtime.paths.lock_directory, project)):
        main_branch = read_project_field(rebase.project, MAIN_FIELD)
        main = locate_forge_branch(runtime.run_process, rebase.project, main_branch, rebase.read_environment)
        login = rebase.read_login() if is_on_github(rebase.project) else NO_LOGIN
        outcome = _rebase_milestone(runtime, rebase, rebase.branch, main)
    if outcome is None:
        return None
    if isinstance(outcome, LaunchedRun):
        return MilestoneRebaseLaunched(
            project=project,
            milestone=rebase.milestone,
            branch=rebase.branch,
            run=outcome.run,
            main_head=outcome.main_head,
            branch_head=outcome.branch_head,
        )
    return MilestoneRebased(
        project=project,
        milestone=rebase.milestone,
        branch=rebase.branch,
        before=outcome.before,
        after=outcome.after,
        waves=NO_WAVE_REBASED,
        login=login,
    )
