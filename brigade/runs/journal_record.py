from dataclasses import dataclass

from brigade.system.client_shapes import COUNT, SCHEMA_VERSION, TEXT
from brigade.system.validate_document import Field

DOCUMENT_SCHEMA_VERSION = 1
JOURNAL_RECORD_SHAPE = {
    "schema_version": SCHEMA_VERSION,
    "at": TEXT,
    "segment": COUNT,
    "kind": TEXT,
    "summary": TEXT,
    "cut": Field(kinds=(bool,)),
}


@dataclass(frozen=True)
class JournalRecord:
    at: str
    segment: int
    kind: str
    summary: str
    cut: bool

    @classmethod
    def from_document(cls, document: dict) -> "JournalRecord":
        return cls(
            at=document["at"],
            segment=document["segment"],
            kind=document["kind"],
            summary=document["summary"],
            cut=document["cut"],
        )

    def to_document(self) -> dict:
        return {
            "schema_version": DOCUMENT_SCHEMA_VERSION,
            "at": self.at,
            "segment": self.segment,
            "kind": self.kind,
            "summary": self.summary,
            "cut": self.cut,
        }
