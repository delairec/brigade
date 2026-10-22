from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class TickActionFailed:
    name: ClassVar[str] = "tick.action_failed"
    action: str
    project: str | None
    wave: str | None
    task: str | None
    error: str

    @classmethod
    def from_document(cls, document: dict) -> "TickActionFailed":
        return cls(
            action=document["action"],
            project=document["project"],
            wave=document["wave"],
            task=document["task"],
            error=document["error"],
        )

    def to_document(self) -> dict:
        return {
            "action": self.action,
            "project": self.project,
            "wave": self.wave,
            "task": self.task,
            "error": self.error,
        }
