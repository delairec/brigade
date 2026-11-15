from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class BranchBaseGone:
    name: ClassVar[str] = "branch.base_gone"
    project: str
    branch: str
    base: str

    @classmethod
    def from_document(cls, document: dict) -> "BranchBaseGone":
        return cls(project=document["project"], branch=document["branch"], base=document["base"])

    def to_document(self) -> dict:
        return {"project": self.project, "branch": self.branch, "base": self.base}
