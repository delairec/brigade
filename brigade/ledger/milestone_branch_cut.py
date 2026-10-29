from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class MilestoneBranchCut:
    name: ClassVar[str] = "milestone.branch_cut"
    project: str
    milestone: str
    branch: str
    login: str | None

    @classmethod
    def from_document(cls, document: dict) -> "MilestoneBranchCut":
        return cls(
            project=document["project"],
            milestone=document["milestone"],
            branch=document["branch"],
            login=document["login"],
        )

    def to_document(self) -> dict:
        return {"project": self.project, "milestone": self.milestone, "branch": self.branch, "login": self.login}
