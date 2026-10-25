from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class InboxRecorded:
    name: ClassVar[str] = "inbox.recorded"
    fingerprint: str
    kind: str
    project: str | None

    @classmethod
    def from_document(cls, document: dict) -> "InboxRecorded":
        return cls(fingerprint=document["fingerprint"], kind=document["kind"], project=document["project"])

    def to_document(self) -> dict:
        return {"fingerprint": self.fingerprint, "kind": self.kind, "project": self.project}
