from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class WavePrRetargeted:
    name: ClassVar[str] = "wave.pr_retargeted"
    wave: str
    pr: int
    base: str
    login: str | None

    @classmethod
    def from_document(cls, document: dict) -> "WavePrRetargeted":
        return cls(wave=document["wave"], pr=document["pr"], base=document["base"], login=document["login"])

    def to_document(self) -> dict:
        return {"wave": self.wave, "pr": self.pr, "base": self.base, "login": self.login}
