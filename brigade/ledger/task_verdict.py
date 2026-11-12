from dataclasses import dataclass, field
from typing import ClassVar

from brigade.ledger.omit_absent_pull_request import ABSENT_PULL_REQUEST, omit_absent_pull_request


@dataclass(frozen=True)
class TaskVerdict:
    name: ClassVar[str] = "task.verdict"
    project: str
    wave: str
    task: str
    pr: int | None = field(default=ABSENT_PULL_REQUEST, kw_only=True)
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
            pr=document.get("pr"),
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
            **omit_absent_pull_request(self.pr),
            "head": self.head,
            "verdict": self.verdict,
            "findings": list(self.findings),
            "login": self.login,
        }
