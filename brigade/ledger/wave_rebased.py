from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class WaveRebased:
    name: ClassVar[str] = "wave.rebased"
    project: str
    wave: str
    branch: str
    before: str
    after: str
    login: str | None

    @classmethod
    def from_document(cls, document: dict) -> "WaveRebased":
        return cls(
            project=document["project"],
            wave=document["wave"],
            branch=document["branch"],
            before=document["before"],
            after=document["after"],
            login=document["login"],
        )

    def to_document(self) -> dict:
        return {
            "project": self.project,
            "wave": self.wave,
            "branch": self.branch,
            "before": self.before,
            "after": self.after,
            "login": self.login,
        }
