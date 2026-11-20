from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class TaskPrOpened:
    name: ClassVar[str] = "task.pr_opened"
    project: str
    task: str
    wave: str
    branch: str
    pr: int
    login: str
    corrects: tuple[int, ...] = ()

    @classmethod
    def from_document(cls, document: dict) -> "TaskPrOpened":
        return cls(
            project=document["project"],
            task=document["task"],
            wave=document["wave"],
            branch=document["branch"],
            pr=document["pr"],
            login=document["login"],
            corrects=tuple(document.get("corrects", ())),
        )

    def to_document(self) -> dict:
        corrects = {"corrects": list(self.corrects)} if self.corrects else {}
        return {
            "project": self.project,
            "task": self.task,
            "wave": self.wave,
            "branch": self.branch,
            "pr": self.pr,
            "login": self.login,
            **corrects,
        }
