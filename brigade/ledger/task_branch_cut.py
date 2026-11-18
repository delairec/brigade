from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class TaskBranchCut:
    name: ClassVar[str] = "task.branch_cut"
    project: str
    task: str
    branch: str

    @classmethod
    def from_document(cls, document: dict) -> "TaskBranchCut":
        return cls(project=document["project"], task=document["task"], branch=document["branch"])

    def to_document(self) -> dict:
        return {"project": self.project, "task": self.task, "branch": self.branch}
