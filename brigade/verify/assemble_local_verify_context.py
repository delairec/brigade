from brigade.runtime import Runtime
from brigade.verify.preflight_task_branch import BranchPreflightDemand


def assemble_local_verify_context(runtime: Runtime, demand: BranchPreflightDemand) -> dict:
    raise NotImplementedError("assemble_local_verify_context")
