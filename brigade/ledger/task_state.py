from dataclasses import dataclass
from typing import ClassVar

from brigade.system.validate_document import DocumentInvalid

TASK_STATES = (
    "queued",
    "running",
    "pr_open",
    "verifying",
    "verified",
    "merged",
    "changes_requested",
    "fixing",
    "parked",
    "paused:quota",
)


@dataclass(frozen=True)
class TaskState:
    name: ClassVar[str] = "task.state"
    wave: str
    task: str
    state: str
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.state not in TASK_STATES:
            raise DocumentInvalid(f"the task state {self.state} is none of {', '.join(TASK_STATES)}")

    @classmethod
    def from_document(cls, document: dict) -> "TaskState":
        return cls(wave=document["wave"], task=document["task"], state=document["state"], reason=document.get("reason"))

    def to_document(self) -> dict:
        document = {"wave": self.wave, "task": self.task, "state": self.state}
        if self.reason is None:
            return document
        return {**document, "reason": self.reason}
