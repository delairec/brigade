from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class WavePaused:
    name: ClassVar[str] = "wave.paused"
    wave: str

    @classmethod
    def from_document(cls, document: dict) -> "WavePaused":
        return cls(wave=document["wave"])
