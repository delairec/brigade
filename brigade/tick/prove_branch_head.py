from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.git.resolve_commit import resolve_commit
from brigade.runtime import Runtime
from brigade.tick.head_proof import HeadProof
from brigade.tick.prove_head import HeadQuery, prove_head
from brigade.tick.read_branch_head_checks import BranchHeadQuery, read_branch_head_checks

NO_TASK_CHECK = None


@dataclass(frozen=True)
class BranchHead:
    project: Entity
    repository: Path
    branch: str
    ref: str
    list_check_runs: Callable[[str, str], list[dict]]


def prove_branch_head(runtime: Runtime, head: BranchHead) -> HeadProof:
    commit = resolve_commit(runtime.run_process, head.repository, head.ref)
    forge_checks = read_branch_head_checks(
        BranchHeadQuery(project=head.project, branch=head.branch, commit=commit, list_check_runs=head.list_check_runs)
    )
    return prove_head(
        runtime,
        HeadQuery(
            project=head.project,
            repository=head.repository,
            commit=commit,
            task_check=NO_TASK_CHECK,
            forge_checks=forge_checks,
        ),
    )
