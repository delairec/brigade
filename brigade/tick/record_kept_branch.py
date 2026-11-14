import sys

from brigade.ledger.append_event import append_event
from brigade.ledger.branch_kept import BranchKept
from brigade.runtime import Runtime
from brigade.tick.actions import KeepBranch


def record_kept_branch(runtime: Runtime, action: KeepBranch) -> None:
    sys.stderr.write(
        f"brigade tick: the branch {action.branch} of {action.project} kept at {action.head}: {action.reason}\n"
    )
    append_event(
        runtime.paths,
        runtime.now,
        BranchKept(project=action.project, branch=action.branch, reason=action.reason, head=action.head),
    )
