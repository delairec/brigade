from dataclasses import dataclass
from typing import ClassVar

DOCUMENT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ActionsRequest:
    operation: ClassVar[str] = "actions"
    output: str

    @classmethod
    def from_document(cls, document: dict) -> "ActionsRequest":
        return cls(output=document["output"])

    def to_document(self) -> dict:
        return {"schema_version": DOCUMENT_SCHEMA_VERSION, "output": self.output}
