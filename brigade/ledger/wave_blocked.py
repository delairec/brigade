from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class WaveBlocked:
    name: ClassVar[str] = "wave.blocked"
    wave: str
    reason: str
    resume_at: str

    @classmethod
    def from_document(cls, document: dict) -> "WaveBlocked":
        return cls(wave=document["wave"], reason=document["reason"], resume_at=document["resume_at"])

    def to_document(self) -> dict:
        return {"wave": self.wave, "reason": self.reason, "resume_at": self.resume_at}
