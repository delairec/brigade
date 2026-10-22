from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class WavePrOpened:
    name: ClassVar[str] = "wave.pr_opened"
    wave: str
    pr: int
    login: str | None

    @classmethod
    def from_document(cls, document: dict) -> "WavePrOpened":
        return cls(wave=document["wave"], pr=document["pr"], login=document["login"])

    def to_document(self) -> dict:
        return {"wave": self.wave, "pr": self.pr, "login": self.login}
