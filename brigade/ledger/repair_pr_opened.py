from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class RepairPrOpened:
    name: ClassVar[str] = "repair.pr_opened"
    project: str
    branch: str
    into: str
    pr: int
    login: str

    @classmethod
    def from_document(cls, document: dict) -> "RepairPrOpened":
        return cls(
            project=document["project"],
            branch=document["branch"],
            into=document["into"],
            pr=document["pr"],
            login=document["login"],
        )

    def to_document(self) -> dict:
        return {
            "project": self.project,
            "branch": self.branch,
            "into": self.into,
            "pr": self.pr,
            "login": self.login,
        }
