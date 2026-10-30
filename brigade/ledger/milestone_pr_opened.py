from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class MilestonePrOpened:
    name: ClassVar[str] = "milestone.pr_opened"
    project: str
    milestone: str
    pr: int
    login: str | None

    @classmethod
    def from_document(cls, document: dict) -> "MilestonePrOpened":
        return cls(
            project=document["project"], milestone=document["milestone"], pr=document["pr"], login=document["login"]
        )

    def to_document(self) -> dict:
        return {"project": self.project, "milestone": self.milestone, "pr": self.pr, "login": self.login}
