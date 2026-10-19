from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.git.push_branch import BranchPush, push_branch
from brigade.runtime import Runtime
from brigade.system.ask_pull_request import PullRequestQuery, ask_pull_request
from brigade.system.read_configuration import CLI_KEY
from brigade.waves.read_plan_review import AUTOMATIC_REVIEW, read_plan_review

REVIEW_SLOT = "review"
REVIEW_REQUIRED = "review_required"
NO_MILESTONE = None


@dataclass(frozen=True)
class PlanPublication:
    repository: Path
    project: str
    base: str
    branch: str
    title: str
    body: str
    forge: object
    forge_name: str
    read_environment: Callable[[str], dict]


def _ask_review(runtime: Runtime, publication: PlanPublication) -> str | None:
    query = PullRequestQuery(
        repository=str(publication.repository),
        branch=publication.branch,
        environment=publication.read_environment(CLI_KEY),
    )
    return ask_pull_request(publication.forge, publication.forge_name, query, runtime).review


def _merge(runtime: Runtime, publication: PlanPublication, number: int) -> None:
    request = {"repository": str(publication.repository), "number": number}
    if _ask_review(runtime, publication) == REVIEW_REQUIRED:
        publication.forge.approve_pull_request(
            {**request, "environment": publication.read_environment(REVIEW_SLOT)}, runtime
        )
    publication.forge.merge_pull_request({**request, "environment": publication.read_environment(CLI_KEY)}, runtime)


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
    if read_plan_review(runtime, publication.project) == AUTOMATIC_REVIEW:
        _merge(runtime, publication, pull_request["number"])
    return pull_request["number"]
