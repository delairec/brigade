from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class InboxDismissed:
    name: ClassVar[str] = "inbox.dismissed"
    fingerprint: str
    kind: str
    project: str | None

    @classmethod
    def from_document(cls, document: dict) -> "InboxDismissed":
        return cls(fingerprint=document["fingerprint"], kind=document["kind"], project=document["project"])

    def to_document(self) -> dict:
        return {"fingerprint": self.fingerprint, "kind": self.kind, "project": self.project}
