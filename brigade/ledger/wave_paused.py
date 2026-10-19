from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class WavePaused:
    name: ClassVar[str] = "wave.paused"
    wave: str
    reason: str
    resume_at: str | None

    @classmethod
    def from_document(cls, document: dict) -> "WavePaused":
        return cls(wave=document["wave"], reason=document["reason"], resume_at=document["resume_at"])

    def to_document(self) -> dict:
        return {"wave": self.wave, "reason": self.reason, "resume_at": self.resume_at}
