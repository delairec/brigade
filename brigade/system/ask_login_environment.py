from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.system.forge_shapes import FORGE_ANSWER_SHAPES
from brigade.system.validate_document import DocumentInvalid, validate_document

OPERATION = "read_login_environment"
DOCUMENT_SCHEMA_VERSION = 1


def ask_login_environment(forge, forge_name: str, login: str, runtime: Runtime) -> dict | None:
    answer = forge.read_login_environment({"schema_version": DOCUMENT_SCHEMA_VERSION, "login": login}, runtime)
    try:
        validate_document(answer, FORGE_ANSWER_SHAPES[OPERATION])
    except DocumentInvalid as problem:
        raise BrigadeError(f"forge plugin {forge_name} answered {OPERATION}: {problem}") from None
    return answer["environment"]
