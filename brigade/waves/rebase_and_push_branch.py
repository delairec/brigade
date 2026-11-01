from brigade.git.push_with_lease import LeasedPush, push_with_lease
from brigade.git.read_head import read_head
from brigade.git.rebase_onto import rebase_onto
from brigade.registry.is_on_github import is_on_github
from brigade.runtime import Runtime
from brigade.system.parse_configuration import CLI_KEY
from brigade.waves.branch_rebase_run import BranchRebaseGateways, BranchRebaseRun


def rebase_and_push_branch(
    runtime: Runtime, gateways: BranchRebaseGateways, run: BranchRebaseRun, upstream: str
) -> str | None:
    head = read_head(runtime.run_process, run.worktree)
    if not rebase_onto(runtime.run_process, run.worktree, upstream):
        gateways.launch_rebase_run(run)
        return None
    if is_on_github(gateways.project):
        push = LeasedPush(
            worktree=run.worktree,
            branch=run.branch,
            expected_head=head,
            environment=gateways.read_environment(CLI_KEY),
        )
        push_with_lease(runtime.run_process, push)
    return head
