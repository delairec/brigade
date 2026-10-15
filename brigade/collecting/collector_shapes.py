from brigade.system.document_shapes import SCHEMA_VERSION, TEXT
from brigade.system.validate_document import Field

COLLECTOR_DOCUMENT_SHAPE = {
    "schema_version": SCHEMA_VERSION,
    "collector": TEXT,
    "collected_at": TEXT,
    "cache": Field(kinds=(bool,), optional=True),
    "summary": Field(kinds=(dict,)),
    "items": Field(kinds=(list,)),
}
