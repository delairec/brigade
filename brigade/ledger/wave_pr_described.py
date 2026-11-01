from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class WavePrDescribed:
    name: ClassVar[str] = "wave.pr_described"
    wave: str
    pr: int
    head: str
    login: str | None

    @classmethod
    def from_document(cls, document: dict) -> "WavePrDescribed":
        return cls(wave=document["wave"], pr=document["pr"], head=document["head"], login=document["login"])

    def to_document(self) -> dict:
        return {"wave": self.wave, "pr": self.pr, "head": self.head, "login": self.login}
