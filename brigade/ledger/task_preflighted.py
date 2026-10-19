from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class TaskPreflighted:
    name: ClassVar[str] = "task.preflighted"
    project: str
    wave: str
    task: str
    pr: int
    head: str
    checks: tuple[dict, ...]

    @classmethod
    def from_document(cls, document: dict) -> "TaskPreflighted":
        return cls(
            project=document["project"],
            wave=document["wave"],
            task=document["task"],
            pr=document["pr"],
            head=document["head"],
            checks=tuple(document["checks"]),
        )

    def to_document(self) -> dict:
        return {
            "project": self.project,
            "wave": self.wave,
            "task": self.task,
            "pr": self.pr,
            "head": self.head,
            "checks": list(self.checks),
        }
