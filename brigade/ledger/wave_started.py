from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class WaveStarted:
    name: ClassVar[str] = "wave.started"
    wave: str
    project: str

    @classmethod
    def from_document(cls, document: dict) -> "WaveStarted":
        return cls(wave=document["wave"], project=document["project"])
