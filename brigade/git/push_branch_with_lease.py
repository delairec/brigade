from collections.abc import Callable

from brigade.git.push_branch import REMOTE, BranchPush
from brigade.git.timeouts import GIT_TIMEOUT_S, REMOTE_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest

STANDING_OR_ABSENT = (0, 1)


def _read_origin_head(run_process: Callable[[ProcessRequest], ProcessRecord], push: BranchPush) -> str:
    record = run_process(
        ProcessRequest(
            argv=("git", "rev-parse", "--verify", "--quiet", f"refs/remotes/{REMOTE}/{push.branch}"),
            cwd=str(push.repository),
            timeout_s=GIT_TIMEOUT_S,
            acceptable_exit_codes=STANDING_OR_ABSENT,
        )
    )
    return record.stdout.strip()


def push_branch_with_lease(run_process: Callable[[ProcessRequest], ProcessRecord], push: BranchPush) -> None:
    origin_head = _read_origin_head(run_process, push)
    run_process(
        ProcessRequest(
            argv=("git", "push", "--quiet", f"--force-with-lease={push.branch}:{origin_head}", REMOTE, push.branch),
            cwd=str(push.repository),
            timeout_s=REMOTE_TIMEOUT_S,
            environment=push.environment,
        )
    )
