from dataclasses import dataclass
from typing import ClassVar

DOCUMENT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ProbeRequest:
    operation: ClassVar[str] = "probe"

    def to_document(self) -> dict:
        return {"schema_version": DOCUMENT_SCHEMA_VERSION}
