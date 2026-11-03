from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class TaskReported:
    name: ClassVar[str] = "task.reported"
    project: str
    task: str
    run: str
    login: str | None

    @classmethod
    def from_document(cls, document: dict) -> "TaskReported":
        return cls(project=document["project"], task=document["task"], run=document["run"], login=document["login"])

    def to_document(self) -> dict:
        return {"project": self.project, "task": self.task, "run": self.run, "login": self.login}
