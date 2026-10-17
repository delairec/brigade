from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class TaskPromoted:
    name: ClassVar[str] = "task.promoted"
    project: str
    task: str
    pr: int
    commit: str

    @classmethod
    def from_document(cls, document: dict) -> "TaskPromoted":
        return cls(project=document["project"], task=document["task"], pr=document["pr"], commit=document["commit"])

    def to_document(self) -> dict:
        return {"project": self.project, "task": self.task, "pr": self.pr, "commit": self.commit}
