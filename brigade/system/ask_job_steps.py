from dataclasses import dataclass

from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.system.forge_shapes import FORGE_ANSWER_SHAPES
from brigade.system.validate_document import DocumentInvalid, validate_document

OPERATION = "read_job_steps"
DOCUMENT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class JobStepsQuery:
    repository: str
    link: str | None
    environment: dict


def ask_job_steps(forge: object, forge_name: str, query: JobStepsQuery, runtime: Runtime) -> list[dict] | None:
    answer = forge.read_job_steps(
        {
            "schema_version": DOCUMENT_SCHEMA_VERSION,
            "repository": query.repository,
            "link": query.link,
            "environment": query.environment,
        },
        runtime,
    )
    try:
        validate_document(answer, FORGE_ANSWER_SHAPES[OPERATION])
    except DocumentInvalid as problem:
        raise BrigadeError(f"forge plugin {forge_name} answered {OPERATION}: {problem}") from None
    return answer["steps"]
