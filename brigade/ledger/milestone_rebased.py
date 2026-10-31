from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class MilestoneRebased:
    name: ClassVar[str] = "milestone.rebased"
    project: str
    milestone: str
    branch: str
    before: str
    after: str
    waves: tuple[str, ...]
    login: str | None

    @classmethod
    def from_document(cls, document: dict) -> "MilestoneRebased":
        return cls(
            project=document["project"],
            milestone=document["milestone"],
            branch=document["branch"],
            before=document["before"],
            after=document["after"],
            waves=tuple(document["waves"]),
            login=document["login"],
        )

    def to_document(self) -> dict:
        return {
            "project": self.project,
            "milestone": self.milestone,
            "branch": self.branch,
            "before": self.before,
            "after": self.after,
            "waves": list(self.waves),
            "login": self.login,
        }
