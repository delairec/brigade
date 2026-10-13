from dataclasses import dataclass

from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.system.document_shapes import DOCUMENT_ANSWER_SHAPES
from brigade.system.validate_document import DocumentInvalid, validate_document


@dataclass(frozen=True)
class DocumentQuestion:
    document_name: str
    operation: str
    request: dict


def ask_document(document, question: DocumentQuestion, runtime: Runtime) -> dict:
    answer = getattr(document, question.operation)(question.request, runtime)
    try:
        validate_document(answer, DOCUMENT_ANSWER_SHAPES[question.operation])
    except DocumentInvalid as problem:
        raise BrigadeError(
            f"document plugin {question.document_name} answered {question.operation}: {problem}"
        ) from None
    return answer
