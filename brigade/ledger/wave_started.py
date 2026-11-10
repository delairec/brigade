from dataclasses import dataclass, field
from typing import ClassVar

BRANCH_KEY = "branch"
TASK_DIGESTS_KEY = "task_digests"
NO_BRANCH = None
NO_TASK_DIGESTS = None


@dataclass(frozen=True)
class WaveStarted:
    name: ClassVar[str] = "wave.started"
    wave: str
    project: str
    tasks: tuple[str, ...]
    branch: str | None = NO_BRANCH
    task_digests: dict[str, str] | None = field(default=NO_TASK_DIGESTS, hash=False)

    @classmethod
    def from_document(cls, document: dict) -> "WaveStarted":
        return cls(
            wave=document["wave"],
            project=document["project"],
            branch=document.get(BRANCH_KEY),
            tasks=tuple(document["tasks"]),
            task_digests=document.get(TASK_DIGESTS_KEY),
        )

    def to_document(self) -> dict:
        recorded_branch = {} if self.branch is None else {BRANCH_KEY: self.branch}
        recorded_digests = {} if self.task_digests is None else {TASK_DIGESTS_KEY: self.task_digests}
        return {
            "wave": self.wave,
            "project": self.project,
            **recorded_branch,
            "tasks": list(self.tasks),
            **recorded_digests,
        }
