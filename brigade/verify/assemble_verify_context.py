from pathlib import Path

from brigade.git.find_merge_base import find_merge_base
from brigade.git.resolve_commit import resolve_commit
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.verify.describe_judged_task import JudgedTask, describe_judged_task
from brigade.verify.preflight_pull_request import REMOTE_BRANCH_PREFIX, PreflightDemand, preflight_pull_request


def assemble_verify_context(runtime: Runtime, demand: PreflightDemand) -> dict:
    preflight = preflight_pull_request(runtime, demand)
    repository = Path(read_project_field(demand.project, "PATH"))
    base_head = resolve_commit(runtime.run_process, repository, f"{REMOTE_BRANCH_PREFIX}{demand.base_branch}")
    judged = JudgedTask(
        project=demand.project.name,
        task=demand.task,
        pr=demand.pr,
        head=preflight["head"],
        base=find_merge_base(runtime.run_process, repository, base_head, preflight["head"]),
        base_head=base_head,
        repository=repository,
        preflight=preflight["checks"],
        configuration=demand.configuration,
    )
    return describe_judged_task(runtime, judged)
