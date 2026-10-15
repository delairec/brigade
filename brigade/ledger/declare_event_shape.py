from dataclasses import MISSING, fields

from brigade.system.validate_document import KIND_NAMES, Field

DECLARED_FIELD = Field(tuple(KIND_NAMES), nullable=True)


def declare_event_shape(kind: type) -> dict:
    return {field.name: DECLARED_FIELD for field in fields(kind) if field.default is MISSING}
