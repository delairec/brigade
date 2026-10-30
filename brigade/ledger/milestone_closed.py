from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class MilestoneClosed:
    name: ClassVar[str] = "milestone.closed"
    project: str
    milestone: str
    pr: int

    @classmethod
    def from_document(cls, document: dict) -> "MilestoneClosed":
        return cls(project=document["project"], milestone=document["milestone"], pr=document["pr"])

    def to_document(self) -> dict:
        return {"project": self.project, "milestone": self.milestone, "pr": self.pr}
