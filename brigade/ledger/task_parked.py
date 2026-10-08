from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class TaskParked:
    name: ClassVar[str] = "task.parked"
    wave: str
    task: str

    @classmethod
    def from_document(cls, document: dict) -> "TaskParked":
        return cls(wave=document["wave"], task=document["task"])
