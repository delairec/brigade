from brigade.system.document_shapes import SCHEMA_VERSION, TEXT
from brigade.system.validate_document import Field

COLLECTOR_DOCUMENT_SHAPE = {
    "schema_version": SCHEMA_VERSION,
    "collector": TEXT,
    "collected_at": TEXT,
    "summary": Field(kinds=(dict,)),
    "items": Field(kinds=(list,)),
}
