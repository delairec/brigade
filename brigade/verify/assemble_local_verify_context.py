from pathlib import Path

from brigade.git.find_merge_base import find_merge_base
from brigade.git.resolve_commit import resolve_commit
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.verify.describe_judged_task import JudgedTask, describe_judged_task
from brigade.verify.preflight_task_branch import BranchPreflightDemand, preflight_task_branch

NO_PULL_REQUEST = None


def assemble_local_verify_context(runtime: Runtime, demand: BranchPreflightDemand) -> dict:
    preflight = preflight_task_branch(runtime, demand)
    repository = Path(read_project_field(demand.project, "PATH"))
    base_head = resolve_commit(runtime.run_process, repository, demand.base_branch)
    judged = JudgedTask(
        project=demand.project.name,
        task=demand.task,
        pr=NO_PULL_REQUEST,
        head=preflight["head"],
        base=find_merge_base(runtime.run_process, repository, base_head, preflight["head"]),
        base_head=base_head,
        repository=repository,
        preflight=preflight["checks"],
        configuration=demand.configuration,
    )
    return describe_judged_task(runtime, judged)
