from brigade.planning.plan_publication import PlanPublication
from brigade.runtime import Runtime
from brigade.system.ask_pull_request import PullRequestQuery, ask_pull_request
from brigade.system.parse_configuration import CLI_KEY
from brigade.system.pull_request_facts import PullRequestFacts
from brigade.waves.read_plan_review import AUTOMATIC_REVIEW, read_plan_review

REVIEW_SLOT = "review"
REVIEW_REQUIRED = "review_required"
PLAN_MERGE_METHOD = "squash"


def _read_pull_request(runtime: Runtime, publication: PlanPublication) -> PullRequestFacts:
    query = PullRequestQuery(
        repository=str(publication.repository),
        branch=publication.branch,
        environment=publication.read_environment(CLI_KEY),
    )
    return ask_pull_request(publication.forge, publication.forge_name, query, runtime)


def review_plan_pull_request(runtime: Runtime, publication: PlanPublication, number: int) -> None:
    if read_plan_review(runtime, publication.project) != AUTOMATIC_REVIEW:
        return
    request = {"repository": str(publication.repository), "number": number}
    pull_request = _read_pull_request(runtime, publication)
    if pull_request.review == REVIEW_REQUIRED:
        publication.forge.approve_pull_request(
            {**request, "environment": publication.read_environment(REVIEW_SLOT)}, runtime
        )
    publication.forge.merge_pull_request(
        {
            **request,
            "method": PLAN_MERGE_METHOD,
            "head": pull_request.head,
            "environment": publication.read_environment(CLI_KEY),
        },
        runtime,
    )
