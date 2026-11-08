from brigade.git.resolve_commit import resolve_commit
from brigade.runtime import Runtime
from brigade.tick.head_proof import HeadEvidence, HeadProof
from brigade.tick.judge_head import judge_head
from brigade.tick.prove_branch_head import NO_TASK_CHECK, BranchHead
from brigade.tick.read_branch_head_checks import BranchHeadQuery, read_branch_head_checks
from brigade.tick.read_commit_checks import read_commit_checks


def judge_branch_head(runtime: Runtime, head: BranchHead) -> HeadProof:
    commit = resolve_commit(runtime.run_process, head.repository, head.ref)
    return judge_head(
        HeadEvidence(
            commit=commit,
            forge_checks=read_branch_head_checks(
                BranchHeadQuery(
                    project=head.project, branch=head.branch, commit=commit, list_check_runs=head.list_check_runs
                )
            ),
            task_check=NO_TASK_CHECK,
            commit_checks=read_commit_checks(runtime.paths.state_root, head.project.name, commit),
        )
    )
