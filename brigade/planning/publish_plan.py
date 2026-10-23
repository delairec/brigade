from brigade.git.push_branch import BranchPush, push_branch
from brigade.planning.plan_publication import PlanPublication
from brigade.planning.review_plan_pull_request import review_plan_pull_request
from brigade.runtime import Runtime
from brigade.system.parse_configuration import CLI_KEY

NO_MILESTONE = None


def publish_plan(runtime: Runtime, publication: PlanPublication) -> int:
    environment = publication.read_environment(CLI_KEY)
    push_branch(
        runtime.run_process,
        BranchPush(repository=publication.repository, branch=publication.branch, environment=environment),
    )
    pull_request = publication.forge.open_pull_request(
        {
            "repository": str(publication.repository),
            "base": publication.base,
            "branch": publication.branch,
            "title": publication.title,
            "body": publication.body,
            "milestone": NO_MILESTONE,
            "environment": environment,
        },
        runtime,
    )
    review_plan_pull_request(runtime, publication, pull_request["number"])
    return pull_request["number"]
