from dataclasses import dataclass

from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.system.forge_shapes import FORGE_ANSWER_SHAPES
from brigade.system.validate_document import DocumentInvalid, validate_document

OPERATION = "list_check_runs"
DOCUMENT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class CheckRunsQuery:
    repository: str
    branch: str
    environment: dict


def ask_check_runs(forge: object, forge_name: str, query: CheckRunsQuery, runtime: Runtime) -> list[dict]:
    answer = forge.list_check_runs(
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
    return answer["check_runs"]
