from brigade.tick.actions import LaunchTask
from brigade.tick.head_proof import ForgeCheck
from brigade.tick.read_branch_head_checks import NO_FORGE_CHECK


def read_pull_request_checks(action: LaunchTask, commit: str) -> tuple[ForgeCheck, ...]:
    checked = action.pull_request_checks
    if checked is None or checked.head != commit:
        return NO_FORGE_CHECK
    return checked.checks
