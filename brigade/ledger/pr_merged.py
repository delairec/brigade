from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class PrMerged:
    name: ClassVar[str] = "pr.merged"
    project: str
    wave: str
    task: str
    pr: int
    rounds: int
    login: str | None

    @classmethod
    def from_document(cls, document: dict) -> "PrMerged":
        return cls(
            project=document["project"],
            wave=document["wave"],
            task=document["task"],
            pr=document["pr"],
            rounds=document["rounds"],
            login=document["login"],
        )

    def to_document(self) -> dict:
        return {
            "project": self.project,
            "wave": self.wave,
            "task": self.task,
            "pr": self.pr,
            "rounds": self.rounds,
            "login": self.login,
        }
