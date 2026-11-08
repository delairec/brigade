from collections.abc import Callable

from brigade.git.push_branch import REMOTE, BranchPush
from brigade.git.timeouts import REMOTE_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest

HEAD_TO_BRANCH_PREFIX = "HEAD:refs/heads/"


def push_head_to_branch(run_process: Callable[[ProcessRequest], ProcessRecord], push: BranchPush) -> None:
    run_process(
        ProcessRequest(
            argv=("git", "push", "--quiet", REMOTE, f"{HEAD_TO_BRANCH_PREFIX}{push.branch}"),
            cwd=str(push.repository),
            timeout_s=REMOTE_TIMEOUT_S,
            environment=push.environment,
        )
    )
