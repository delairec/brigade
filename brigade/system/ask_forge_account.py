from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.system.account_answer import AccountAnswer
from brigade.system.account_request import AccountRequest
from brigade.system.forge_shapes import FORGE_ANSWER_SHAPES
from brigade.system.validate_document import DocumentInvalid, validate_document

OPERATION = "describe_account"


def ask_forge_account(forge, forge_name: str, environment: dict, runtime: Runtime) -> AccountAnswer:
    answer = forge.describe_account(AccountRequest(environment).to_document(), runtime)
    try:
        validate_document(answer, FORGE_ANSWER_SHAPES[OPERATION])
    except DocumentInvalid as problem:
        raise BrigadeError(f"forge plugin {forge_name} answered {OPERATION}: {problem}") from None
    return AccountAnswer.from_document(answer)
