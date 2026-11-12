from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.git.check_ancestor import check_ancestor
from brigade.git.fetch_branches import REMOTE
from brigade.git.resolve_commit import resolve_commit
from brigade.registry.is_on_a_forge import is_on_a_forge
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.tick.actions import LaunchTask, RebaseMilestone, RebaseTask
from brigade.tick.head_proof import PENDING, RED, HeadEvidence, HeadProof, HoldingHead
from brigade.tick.judge_branch_head import judge_branch_head
from brigade.tick.judge_head import judge_head
from brigade.tick.prove_branch_head import BranchHead
from brigade.tick.read_commit_checks import read_commit_checks
from brigade.tick.read_pull_request_checks import read_pull_request_checks
from brigade.tick.read_task_check import read_task_check

HOLDING_STATES = (RED, PENDING)
DESCENDING = 0
BUILT_AS_IT_STANDS = None


@dataclass(frozen=True)
class _HeldAction:
    project: Entity
    repository: Path
    list_check_runs: Callable[[str, str], list[dict]]


def _locate_branch_ref(project: Entity, branch: str) -> str:
    if is_on_a_forge(project):
        return f"{REMOTE}/{branch}"
    return branch


def _list_judged_branches(project: Entity, action) -> tuple[str, ...]:
    if isinstance(action, RebaseMilestone):
        return (read_project_field(project, "MAIN"), action.branch)
    return (action.branch,)


def _find_holding_branch(runtime: Runtime, held: _HeldAction, branches: tuple[str, ...]) -> HoldingHead | None:
    for branch in branches:
        proof = judge_branch_head(
            runtime,
            BranchHead(
                project=held.project,
                repository=held.repository,
                branch=branch,
                ref=_locate_branch_ref(held.project, branch),
                list_check_runs=held.list_check_runs,
            ),
        )
        if proof.state in HOLDING_STATES:
            return HoldingHead(branch=branch, proof=proof)
    return None


def _judge_task_head(runtime: Runtime, held: _HeldAction, action: LaunchTask, commit: str) -> HeadProof:
    state_root = runtime.paths.state_root
    return judge_head(
        HeadEvidence(
            commit=commit,
            forge_checks=read_pull_request_checks(action, commit),
            task_check=read_task_check(state_root, held.project.name, action.task),
            commit_checks=read_commit_checks(state_root, held.project.name, commit),
        )
    )


def _find_holding_launch(runtime: Runtime, held: _HeldAction, action: LaunchTask) -> HoldingHead | None:
    commit = resolve_commit(runtime.run_process, held.repository, action.task_branch)
    if commit is None:
        return None
    base_ref = _locate_branch_ref(held.project, action.branch)
    if check_ancestor(runtime.run_process, held.repository, base_ref, action.task_branch).exit_code == DESCENDING:
        return None
    task_head = _judge_task_head(runtime, held, action, commit)
    if task_head.state == RED:
        return BUILT_AS_IT_STANDS
    if task_head.state == PENDING:
        return HoldingHead(branch=action.task_branch, proof=task_head)
    return _find_holding_branch(runtime, held, (action.branch,))


def find_holding_head(
    runtime: Runtime,
    project: Entity,
    action: LaunchTask | RebaseTask | RebaseMilestone,
    list_check_runs: Callable[[str, str], list[dict]],
) -> HoldingHead | None:
    held = _HeldAction(
        project=project, repository=Path(read_project_field(project, "PATH")), list_check_runs=list_check_runs
    )
    if isinstance(action, LaunchTask):
        return _find_holding_launch(runtime, held, action)
    return _find_holding_branch(runtime, held, _list_judged_branches(project, action))
