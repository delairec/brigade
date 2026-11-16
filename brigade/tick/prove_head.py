from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.git.add_detached_worktree import DetachedWorktree, add_detached_worktree
from brigade.git.remove_detached_worktree import remove_detached_worktree
from brigade.runtime import Runtime
from brigade.tick.head_proof import UNPROVEN, ForgeCheck, HeadEvidence, HeadProof, TaskCheck
from brigade.tick.judge_head import judge_head
from brigade.tick.read_commit_checks import read_commit_checks
from brigade.tick.run_commit_checks import run_commit_checks

PROOF_REASON = "brigade proving a head"

HEAD_CHECKS_DIRECTORY = "head-checks"


@dataclass(frozen=True)
class HeadQuery:
    project: Entity
    repository: Path
    commit: str
    build_check: TaskCheck | None
    forge_checks: tuple[ForgeCheck, ...]


def _check_on_a_checkout(runtime: Runtime, query: HeadQuery, evidence: HeadEvidence) -> HeadProof:
    checkout = runtime.paths.state_root / HEAD_CHECKS_DIRECTORY / query.project.name / query.commit
    worktree = DetachedWorktree(repository=query.repository, path=checkout, start=query.commit, reason=PROOF_REASON)
    add_detached_worktree(runtime.run_process, worktree)
    try:
        commit_checks = run_commit_checks(runtime, query.project, checkout, query.commit)
    finally:
        remove_detached_worktree(runtime.run_process, worktree)
    return judge_head(
        HeadEvidence(
            commit=evidence.commit,
            forge_checks=evidence.forge_checks,
            build_check=evidence.build_check,
            commit_checks=commit_checks,
        )
    )


def prove_head(runtime: Runtime, query: HeadQuery) -> HeadProof:
    evidence = HeadEvidence(
        commit=query.commit,
        forge_checks=query.forge_checks,
        build_check=query.build_check,
        commit_checks=read_commit_checks(runtime.paths.state_root, query.project.name, query.commit),
    )
    proof = judge_head(evidence)
    if proof.state != UNPROVEN:
        return proof
    return _check_on_a_checkout(runtime, query, evidence)
