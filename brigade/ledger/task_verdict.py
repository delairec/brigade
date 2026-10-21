from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class TaskVerdict:
    name: ClassVar[str] = "task.verdict"
    project: str
    wave: str
    task: str
    pr: int
    head: str
    verdict: str
    findings: tuple[dict, ...]
    login: str | None

    @classmethod
    def from_document(cls, document: dict) -> "TaskVerdict":
        return cls(
            project=document["project"],
            wave=document["wave"],
            task=document["task"],
            pr=document["pr"],
            head=document["head"],
            verdict=document["verdict"],
            findings=tuple(document["findings"]),
            login=document["login"],
        )

    def to_document(self) -> dict:
        return {
            "project": self.project,
            "wave": self.wave,
            "task": self.task,
            "pr": self.pr,
            "head": self.head,
            "verdict": self.verdict,
            "findings": list(self.findings),
            "login": self.login,
        }
