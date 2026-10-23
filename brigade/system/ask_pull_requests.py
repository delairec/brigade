from dataclasses import dataclass

from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.system.forge_shapes import FORGE_ANSWER_SHAPES
from brigade.system.validate_document import DocumentInvalid, validate_document

OPERATION = "list_pull_requests"
DOCUMENT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class PullRequestsQuery:
    repository: str
    state: str
    environment: dict


def ask_pull_requests(forge: object, forge_name: str, query: PullRequestsQuery, runtime: Runtime) -> list[dict]:
    answer = forge.list_pull_requests(
        {
            "schema_version": DOCUMENT_SCHEMA_VERSION,
            "repository": query.repository,
            "state": query.state,
            "environment": query.environment,
        },
        runtime,
    )
    try:
        validate_document(answer, FORGE_ANSWER_SHAPES[OPERATION])
    except DocumentInvalid as problem:
        raise BrigadeError(f"forge plugin {forge_name} answered {OPERATION}: {problem}") from None
    return answer["pull_requests"]
