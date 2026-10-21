from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class TaskParked:
    name: ClassVar[str] = "task.parked"
    wave: str
    task: str
    reason: str
    blockers: tuple[str, ...]

    @classmethod
    def from_document(cls, document: dict) -> "TaskParked":
        return cls(
            wave=document["wave"],
            task=document["task"],
            reason=document["reason"],
            blockers=tuple(document["blockers"]),
        )

    def to_document(self) -> dict:
        return {"wave": self.wave, "task": self.task, "reason": self.reason, "blockers": list(self.blockers)}
