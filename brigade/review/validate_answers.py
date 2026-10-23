from collections import Counter

from brigade.system.validate_document import DocumentInvalid, Field, validate_document

ANSWERS_SHAPE = {
    "answers": Field(
        kinds=(list,),
        items=Field(kinds=(dict,), fields={"finding": Field(kinds=(str,)), "answer": Field(kinds=(str,))}),
    ),
}


def validate_answers(document: object, findings: list[dict]) -> None:
    validate_document(document, ANSWERS_SHAPE)
    answered = Counter(answer["finding"] for answer in document["answers"])
    identifiers = [finding["id"] for finding in findings]
    unanswered = next((identifier for identifier in identifiers if identifier not in answered), None)
    if unanswered is not None:
        raise DocumentInvalid(f"finding {unanswered} has no answer")
    unknown = next((finding for finding in answered if finding not in identifiers), None)
    if unknown is not None:
        raise DocumentInvalid(f"finding {unknown} is no finding of the context")
    twice = next((finding for finding, count in answered.items() if count > 1), None)
    if twice is not None:
        raise DocumentInvalid(f"finding {twice} is answered twice")
