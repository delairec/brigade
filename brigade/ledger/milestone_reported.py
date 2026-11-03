from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class MilestoneReported:
    name: ClassVar[str] = "milestone.reported"
    project: str
    milestone: str
    run: str
    login: str | None

    @classmethod
    def from_document(cls, document: dict) -> "MilestoneReported":
        return cls(
            project=document["project"], milestone=document["milestone"], run=document["run"], login=document["login"]
        )

    def to_document(self) -> dict:
        return {"project": self.project, "milestone": self.milestone, "run": self.run, "login": self.login}
