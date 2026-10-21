from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class WaveReported:
    name: ClassVar[str] = "wave.reported"
    wave: str
    run: str | None

    @classmethod
    def from_document(cls, document: dict) -> "WaveReported":
        return cls(wave=document["wave"], run=document["run"])

    def to_document(self) -> dict:
        return {"wave": self.wave, "run": self.run}
