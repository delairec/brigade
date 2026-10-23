from collections.abc import Callable

from brigade.git.push_branch import REMOTE, BranchPush
from brigade.git.timeouts import REMOTE_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest


def force_push_branch(run_process: Callable[[ProcessRequest], ProcessRecord], push: BranchPush) -> None:
    run_process(
        ProcessRequest(
            argv=("git", "push", "--quiet", "--force", REMOTE, push.branch),
            cwd=str(push.repository),
            timeout_s=REMOTE_TIMEOUT_S,
            environment=push.environment,
        )
    )
