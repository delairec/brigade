from dataclasses import dataclass
from typing import ClassVar

from brigade.ledger.omit_absent_pull_request import omit_absent_pull_request


@dataclass(frozen=True)
class TaskPreflighted:
    name: ClassVar[str] = "task.preflighted"
    project: str
    wave: str
    task: str
    pr: int | None
    head: str
    checks: tuple[dict, ...]

    @classmethod
    def from_document(cls, document: dict) -> "TaskPreflighted":
        return cls(
            project=document["project"],
            wave=document["wave"],
            task=document["task"],
            pr=document.get("pr"),
            head=document["head"],
            checks=tuple(document["checks"]),
        )

    def to_document(self) -> dict:
        return {
            "project": self.project,
            "wave": self.wave,
            "task": self.task,
            **omit_absent_pull_request(self.pr),
            "head": self.head,
            "checks": list(self.checks),
        }
