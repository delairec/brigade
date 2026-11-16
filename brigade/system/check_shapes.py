from brigade.system.document_shapes import SCHEMA_VERSION, TEXT
from brigade.system.validate_document import Field

CHECK_DOCUMENT_SCHEMA_VERSION = 1
PASSED = "pass"
FAILED = "fail"
CHECK_DOCUMENT_SHAPE = {
    "schema_version": SCHEMA_VERSION,
    "name": TEXT,
    "verdict": Field(kinds=(str,), values=(PASSED, FAILED)),
    "findings": Field(kinds=(list,), items=TEXT),
}
