from dataclasses import dataclass
from typing import ClassVar

from brigade.ledger.omit_absent_pull_request import omit_absent_pull_request


@dataclass(frozen=True)
class WaveMerged:
    name: ClassVar[str] = "wave.merged"
    wave: str
    pr: int | None
    login: str | None

    @classmethod
    def from_document(cls, document: dict) -> "WaveMerged":
        return cls(wave=document["wave"], pr=document.get("pr"), login=document["login"])

    def to_document(self) -> dict:
        return {"wave": self.wave, **omit_absent_pull_request(self.pr), "login": self.login}
