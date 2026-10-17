from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class MilestoneCreated:
    name: ClassVar[str] = "milestone.created"
    project: str
    title: str
    login: str

    @classmethod
    def from_document(cls, document: dict) -> "MilestoneCreated":
        return cls(project=document["project"], title=document["title"], login=document["login"])

    def to_document(self) -> dict:
        return {"project": self.project, "title": self.title, "login": self.login}
