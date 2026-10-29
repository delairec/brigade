from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class WaveMerged:
    name: ClassVar[str] = "wave.merged"
    wave: str
    pr: int
    login: str

    @classmethod
    def from_document(cls, document: dict) -> "WaveMerged":
        return cls(wave=document["wave"], pr=document["pr"], login=document["login"])

    def to_document(self) -> dict:
        return {"wave": self.wave, "pr": self.pr, "login": self.login}
