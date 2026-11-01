from dataclasses import dataclass
from typing import ClassVar

from brigade.ledger.omit_absent_pull_request import omit_absent_pull_request


@dataclass(frozen=True)
class PrMerged:
    name: ClassVar[str] = "pr.merged"
    project: str
    wave: str
    task: str
    pr: int | None
    rounds: int
    login: str | None

    @classmethod
    def from_document(cls, document: dict) -> "PrMerged":
        return cls(
            project=document["project"],
            wave=document["wave"],
            task=document["task"],
            pr=document.get("pr"),
            rounds=document["rounds"],
            login=document["login"],
        )

    def to_document(self) -> dict:
        return {
            "project": self.project,
            "wave": self.wave,
            "task": self.task,
            **omit_absent_pull_request(self.pr),
            "rounds": self.rounds,
            "login": self.login,
        }
