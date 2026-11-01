from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class MilestonePrDescribed:
    name: ClassVar[str] = "milestone.pr_described"
    project: str
    milestone: str
    pr: int
    head: str
    login: str | None

    @classmethod
    def from_document(cls, document: dict) -> "MilestonePrDescribed":
        return cls(
            project=document["project"],
            milestone=document["milestone"],
            pr=document["pr"],
            head=document["head"],
            login=document["login"],
        )

    def to_document(self) -> dict:
        return {
            "project": self.project,
            "milestone": self.milestone,
            "pr": self.pr,
            "head": self.head,
            "login": self.login,
        }
