from dataclasses import dataclass
from typing import ClassVar

BRANCH_KEY = "branch"
NO_BRANCH = None


@dataclass(frozen=True)
class WaveStarted:
    name: ClassVar[str] = "wave.started"
    wave: str
    project: str
    tasks: tuple[str, ...]
    branch: str | None = NO_BRANCH

    @classmethod
    def from_document(cls, document: dict) -> "WaveStarted":
        return cls(
            wave=document["wave"],
            project=document["project"],
            branch=document.get(BRANCH_KEY),
            tasks=tuple(document["tasks"]),
        )

    def to_document(self) -> dict:
        recorded_branch = {} if self.branch is None else {BRANCH_KEY: self.branch}
        return {"wave": self.wave, "project": self.project, **recorded_branch, "tasks": list(self.tasks)}
