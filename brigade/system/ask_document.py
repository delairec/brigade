from dataclasses import dataclass

from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.system.document_creation import DocumentCreation
from brigade.system.document_request import DocumentRequest
from brigade.system.document_shapes import DOCUMENT_ANSWER_SHAPES
from brigade.system.document_text import DocumentText
from brigade.system.entry_detection import EntryDetection
from brigade.system.validate_document import DocumentInvalid, validate_document

ANSWER_KINDS = {
    "create_document": DocumentCreation,
    "describe_document": DocumentText,
    "read_document": DocumentText,
    "detect_entry": EntryDetection,
}


@dataclass(frozen=True)
class DocumentQuestion:
    document_name: str
    operation: str
    request: DocumentRequest


def ask_document(
    document, question: DocumentQuestion, runtime: Runtime
) -> DocumentCreation | DocumentText | EntryDetection:
    answer = getattr(document, question.operation)(question.request.to_document(), runtime)
    try:
        validate_document(answer, DOCUMENT_ANSWER_SHAPES[question.operation])
    except DocumentInvalid as problem:
        raise BrigadeError(
            f"document plugin {question.document_name} answered {question.operation}: {problem}"
        ) from None
    return ANSWER_KINDS[question.operation].from_document(answer)
