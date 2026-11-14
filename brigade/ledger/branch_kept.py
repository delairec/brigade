from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class BranchKept:
    name: ClassVar[str] = "branch.kept"
    project: str
    branch: str
    reason: str
    head: str

    @classmethod
    def from_document(cls, document: dict) -> "BranchKept":
        return cls(
            project=document["project"], branch=document["branch"], reason=document["reason"], head=document["head"]
        )

    def to_document(self) -> dict:
        return {"project": self.project, "branch": self.branch, "reason": self.reason, "head": self.head}
