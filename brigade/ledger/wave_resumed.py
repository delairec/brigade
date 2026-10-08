from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class WaveResumed:
    name: ClassVar[str] = "wave.resumed"
    wave: str

    @classmethod
    def from_document(cls, document: dict) -> "WaveResumed":
        return cls(wave=document["wave"])
