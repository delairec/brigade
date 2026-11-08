from collections.abc import Callable
from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.git.check_ancestor import check_ancestor
from brigade.git.fetch_branches import REMOTE
from brigade.git.resolve_commit import resolve_commit
from brigade.registry.is_on_github import is_on_github
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.tick.actions import LaunchTask, RebaseMilestone, RebaseTask
from brigade.tick.head_proof import PENDING, RED, HoldingHead
from brigade.tick.judge_branch_head import judge_branch_head
from brigade.tick.prove_branch_head import BranchHead

HOLDING_STATES = (RED, PENDING)
DESCENDING = 0


def _locate_base_ref(project: Entity, base: str) -> str:
    if is_on_github(project):
        return f"{REMOTE}/{base}"
    return base


def _read_base(project: Entity, action) -> str:
    if isinstance(action, RebaseMilestone):
        return read_project_field(project, "MAIN")
    return action.branch


def _is_launched_off_its_base(runtime: Runtime, repository: Path, base_ref: str, action) -> bool:
    if not isinstance(action, LaunchTask):
        return True
    if resolve_commit(runtime.run_process, repository, action.task_branch) is None:
        return False
    return check_ancestor(runtime.run_process, repository, base_ref, action.task_branch).exit_code != DESCENDING


def find_holding_base(
    runtime: Runtime,
    project: Entity,
    action: LaunchTask | RebaseTask | RebaseMilestone,
    list_check_runs: Callable[[str, str], list[dict]],
) -> HoldingHead | None:
    repository = Path(read_project_field(project, "PATH"))
    base = _read_base(project, action)
    base_ref = _locate_base_ref(project, base)
    if not _is_launched_off_its_base(runtime, repository, base_ref, action):
        return None
    proof = judge_branch_head(
        runtime,
        BranchHead(project=project, repository=repository, branch=base, ref=base_ref, list_check_runs=list_check_runs),
    )
    if proof.state not in HOLDING_STATES:
        return None
    return HoldingHead(branch=base, proof=proof)
