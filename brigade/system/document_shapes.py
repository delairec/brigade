from brigade.system.validate_document import Field

SCHEMA_VERSION = Field(kinds=(int,), values=(1,))
TEXT = Field(kinds=(str,))

DOCUMENT_ANSWER_SHAPES = {
    "create_document": {"schema_version": SCHEMA_VERSION},
    "describe_document": {"schema_version": SCHEMA_VERSION, "text": TEXT},
    "read_document": {"schema_version": SCHEMA_VERSION, "text": TEXT},
    "detect_entry": {"schema_version": SCHEMA_VERSION, "holds_entry": Field(kinds=(bool,))},
}
