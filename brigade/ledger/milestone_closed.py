from dataclasses import dataclass
from typing import ClassVar

from brigade.ledger.omit_absent_pull_request import ABSENT_PULL_REQUEST, omit_absent_pull_request


@dataclass(frozen=True)
class MilestoneClosed:
    name: ClassVar[str] = "milestone.closed"
    project: str
    milestone: str
    pr: int | None = ABSENT_PULL_REQUEST

    @classmethod
    def from_document(cls, document: dict) -> "MilestoneClosed":
        return cls(project=document["project"], milestone=document["milestone"], pr=document.get("pr"))

    def to_document(self) -> dict:
        return {"project": self.project, "milestone": self.milestone, **omit_absent_pull_request(self.pr)}
