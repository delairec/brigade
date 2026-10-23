from dataclasses import dataclass

from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.system.forge_shapes import FORGE_ANSWER_SHAPES
from brigade.system.validate_document import DocumentInvalid, validate_document

OPERATION = "read_check_logs"
DOCUMENT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class CheckLogsQuery:
    repository: str
    number: int
    checks: tuple[str, ...]
    lines: int
    environment: dict


def ask_check_logs(forge: object, forge_name: str, query: CheckLogsQuery, runtime: Runtime) -> list[dict]:
    answer = forge.read_check_logs(
        {
            "schema_version": DOCUMENT_SCHEMA_VERSION,
            "repository": query.repository,
            "number": query.number,
            "checks": list(query.checks),
            "lines": query.lines,
            "environment": query.environment,
        },
        runtime,
    )
    try:
        validate_document(answer, FORGE_ANSWER_SHAPES[OPERATION])
    except DocumentInvalid as problem:
        raise BrigadeError(f"forge plugin {forge_name} answered {OPERATION}: {problem}") from None
    return answer["logs"]
