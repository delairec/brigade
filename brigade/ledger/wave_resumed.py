from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class WaveResumed:
    name: ClassVar[str] = "wave.resumed"
    wave: str
    reason: str

    @classmethod
    def from_document(cls, document: dict) -> "WaveResumed":
        return cls(wave=document["wave"], reason=document["reason"])

    def to_document(self) -> dict:
        return {"wave": self.wave, "reason": self.reason}
