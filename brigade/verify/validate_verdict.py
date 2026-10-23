from brigade.system.validate_document import DocumentInvalid, Field, validate_document
from brigade.verify.assemble_verify_context import GRADES

PASSING_VERDICT = "pass"
CHANGES_VERDICT = "changes"
VERDICT_SHAPE = {
    "head": Field(kinds=(str,)),
    "verdict": Field(kinds=(str,), values=(PASSING_VERDICT, CHANGES_VERDICT)),
    "findings": Field(
        kinds=(list,),
        items=Field(
            kinds=(dict,),
            fields={
                "grade": Field(kinds=(str,), values=GRADES),
                "file": Field(kinds=(str,)),
                "line": Field(kinds=(int,)),
                "broken": Field(kinds=(str,)),
            },
        ),
    ),
}


def validate_verdict(document: object) -> None:
    validate_document(document, VERDICT_SHAPE)
    if document["verdict"] == CHANGES_VERDICT and not document["findings"]:
        raise DocumentInvalid(f"a verdict {CHANGES_VERDICT} names no finding")
