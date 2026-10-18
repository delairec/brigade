from dataclasses import dataclass

from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.system.forge_shapes import FORGE_ANSWER_SHAPES
from brigade.system.pull_request_facts import PullRequestFacts
from brigade.system.validate_document import DocumentInvalid, validate_document

OPERATION = "find_pull_request"
DOCUMENT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class PullRequestQuery:
    repository: str
    branch: str
    environment: dict


def ask_pull_request(forge, forge_name: str, query: PullRequestQuery, runtime: Runtime) -> PullRequestFacts | None:
    answer = forge.find_pull_request(
        {
            "schema_version": DOCUMENT_SCHEMA_VERSION,
            "repository": query.repository,
            "branch": query.branch,
            "environment": query.environment,
        },
        runtime,
    )
    try:
        validate_document(answer, FORGE_ANSWER_SHAPES[OPERATION])
    except DocumentInvalid as problem:
        raise BrigadeError(f"forge plugin {forge_name} answered {OPERATION}: {problem}") from None
    if answer["pull_request"] is None:
        return None
    return PullRequestFacts.from_document(answer["pull_request"])
