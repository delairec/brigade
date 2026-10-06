from dataclasses import dataclass

from brigade.errors import BrigadeError
from brigade.system.client_shapes import CLIENT_ANSWER_SHAPES
from brigade.system.validate_document import DocumentInvalid, validate_document


@dataclass(frozen=True)
class ClientQuestion:
    client_name: str
    operation: str
    request: dict


def ask_client(client, question: ClientQuestion) -> dict:
    document = client.answer(question.operation, question.request)
    try:
        validate_document(document, CLIENT_ANSWER_SHAPES[question.operation])
    except DocumentInvalid as problem:
        raise BrigadeError(f"client adapter {question.client_name} answered {question.operation}: {problem}") from None
    return document
