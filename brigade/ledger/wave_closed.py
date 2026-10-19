from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class WaveClosed:
    name: ClassVar[str] = "wave.closed"
    wave: str
    pr: int

    @classmethod
    def from_document(cls, document: dict) -> "WaveClosed":
        return cls(wave=document["wave"], pr=document["pr"])

    def to_document(self) -> dict:
        return {"wave": self.wave, "pr": self.pr}
