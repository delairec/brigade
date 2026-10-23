from dataclasses import dataclass

from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.system.forge_shapes import FORGE_ANSWER_SHAPES
from brigade.system.validate_document import DocumentInvalid, validate_document

OPERATION = "read_pull_request"
DOCUMENT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class PullRequestDetailsQuery:
    repository: str
    number: int
    environment: dict


def ask_pull_request_details(forge: object, forge_name: str, query: PullRequestDetailsQuery, runtime: Runtime) -> dict:
    answer = forge.read_pull_request(
        {
            "schema_version": DOCUMENT_SCHEMA_VERSION,
            "repository": query.repository,
            "number": query.number,
            "environment": query.environment,
        },
        runtime,
    )
    try:
        validate_document(answer, FORGE_ANSWER_SHAPES[OPERATION])
    except DocumentInvalid as problem:
        raise BrigadeError(f"forge plugin {forge_name} answered {OPERATION}: {problem}") from None
    return answer["pull_request"]
