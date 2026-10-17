from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class WaveStarted:
    name: ClassVar[str] = "wave.started"
    wave: str
    project: str
    branch: str
    tasks: tuple[str, ...]

    @classmethod
    def from_document(cls, document: dict) -> "WaveStarted":
        return cls(
            wave=document["wave"],
            project=document["project"],
            branch=document["branch"],
            tasks=tuple(document["tasks"]),
        )

    def to_document(self) -> dict:
        return {"wave": self.wave, "project": self.project, "branch": self.branch, "tasks": list(self.tasks)}
