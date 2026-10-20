from brigade.planning.plan_publication import PlanPublication
from brigade.runtime import Runtime
from brigade.system.ask_pull_request import PullRequestQuery, ask_pull_request
from brigade.system.read_configuration import CLI_KEY
from brigade.waves.read_plan_review import AUTOMATIC_REVIEW, read_plan_review

REVIEW_SLOT = "review"
REVIEW_REQUIRED = "review_required"


def _ask_review(runtime: Runtime, publication: PlanPublication) -> str | None:
    query = PullRequestQuery(
        repository=str(publication.repository),
        branch=publication.branch,
        environment=publication.read_environment(CLI_KEY),
    )
    return ask_pull_request(publication.forge, publication.forge_name, query, runtime).review


def review_plan_pull_request(runtime: Runtime, publication: PlanPublication, number: int) -> None:
    if read_plan_review(runtime, publication.project) != AUTOMATIC_REVIEW:
        return
    request = {"repository": str(publication.repository), "number": number}
    if _ask_review(runtime, publication) == REVIEW_REQUIRED:
        publication.forge.approve_pull_request(
            {**request, "environment": publication.read_environment(REVIEW_SLOT)}, runtime
        )
    publication.forge.merge_pull_request({**request, "environment": publication.read_environment(CLI_KEY)}, runtime)
