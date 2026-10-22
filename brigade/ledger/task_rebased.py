from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class TaskRebased:
    name: ClassVar[str] = "task.rebased"
    wave: str
    task: str
    before: str
    after: str
    login: str | None

    @classmethod
    def from_document(cls, document: dict) -> "TaskRebased":
        return cls(
            wave=document["wave"],
            task=document["task"],
            before=document["before"],
            after=document["after"],
            login=document["login"],
        )

    def to_document(self) -> dict:
        return {"wave": self.wave, "task": self.task, "before": self.before, "after": self.after, "login": self.login}
