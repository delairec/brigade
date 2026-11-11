from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class MilestoneRebaseLaunched:
    name: ClassVar[str] = "milestone.rebase_launched"
    project: str
    milestone: str
    branch: str
    run: str
    main_head: str | None
    branch_head: str

    @classmethod
    def from_document(cls, document: dict) -> "MilestoneRebaseLaunched":
        return cls(
            project=document["project"],
            milestone=document["milestone"],
            branch=document["branch"],
            run=document["run"],
            main_head=document["main_head"],
            branch_head=document["branch_head"],
        )

    def to_document(self) -> dict:
        return {
            "project": self.project,
            "milestone": self.milestone,
            "branch": self.branch,
            "run": self.run,
            "main_head": self.main_head,
            "branch_head": self.branch_head,
        }
